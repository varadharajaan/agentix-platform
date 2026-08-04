import httpx
import pytest
import respx

from synapse.config import SynapseConfig
from synapse.memory import EverMemStore


@pytest.fixture
def store(config: SynapseConfig) -> EverMemStore:
    return EverMemStore(config, group_id="g1")


async def test_remember_posts_memory_payload(store: EverMemStore):
    with respx.mock(base_url="http://evermemos.test") as mock:
        route = mock.post("/api/v1/memories").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        await store.remember("user prefers dark mode", role="user")

    payload = route.calls.last.request
    import json

    body = json.loads(payload.content)
    assert body["content"] == "user prefers dark mode"
    assert body["role"] == "user"
    assert body["sender"] == "tester"
    assert body["group_id"] == "g1"
    assert isinstance(body["create_time"], int)


async def test_recall_uses_get_with_json_body_and_parses_both_fields(
    store: EverMemStore,
):
    with respx.mock(base_url="http://evermemos.test") as mock:
        mock.request("GET", "/api/v1/memories/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "memories": [
                            {"memory_type": "profile", "memory_content": "likes tea"},
                            {"memory_type": "event_log", "content": "joined in March"},
                        ]
                    }
                },
            )
        )
        results = await store.recall("what does the user like")

    assert results == ["likes tea", "joined in March"]


async def test_recall_sends_hybrid_retrieval_by_default(store: EverMemStore):
    import json

    with respx.mock(base_url="http://evermemos.test") as mock:
        route = mock.request("GET", "/api/v1/memories/search").mock(
            return_value=httpx.Response(200, json={"data": {"memories": []}})
        )
        await store.recall("anything", top_k=3)

    body = json.loads(route.calls.last.request.content)
    assert body["retrieve_method"] == "hybrid"
    assert body["top_k"] == 3
    assert body["user_id"] == "tester"


async def test_health(store: EverMemStore):
    with respx.mock(base_url="http://evermemos.test") as mock:
        mock.get("/health").mock(return_value=httpx.Response(200))
        assert await store.health() is True

    with respx.mock(base_url="http://evermemos.test") as mock:
        mock.get("/health").mock(return_value=httpx.Response(503))
        assert await store.health() is False


async def test_as_tools_roundtrip(store: EverMemStore):
    tools = store.as_tools()
    assert {t.name for t in tools} == {"save_memory", "search_memory"}

    with respx.mock(base_url="http://evermemos.test") as mock:
        mock.post("/api/v1/memories").mock(return_value=httpx.Response(200))
        mock.request("GET", "/api/v1/memories/search").mock(
            return_value=httpx.Response(
                200, json={"data": {"memories": [{"memory_content": "fact"}]}}
            )
        )
        save, search = tools
        assert await save.ainvoke({"content": "remember this"}) == "saved"
        assert await search.ainvoke({"query": "this"}) == "fact"
