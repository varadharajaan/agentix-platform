"""AtlasMemoryStore tests — pipeline shapes and RRF fusion, no MongoDB needed."""

from __future__ import annotations

import pytest

from synapse.memory.atlas import VECTOR_INDEX, AtlasMemoryStore


class FakeEmbeddings:
    async def aembed_query(self, text: str) -> list[float]:
        return [float(len(text)), 1.0, 0.0]


class FakeAsyncCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, _n):
        return self

    def __aiter__(self):
        async def gen():
            for doc in self._docs:
                yield doc

        return gen()


class FakeCollection:
    def __init__(self):
        self.inserted = []
        self.pipelines = []
        self.aggregate_result = []
        self.find_result = []
        self.indexes = []

    async def insert_one(self, doc):
        self.inserted.append(doc)

    async def aggregate(self, pipeline):
        self.pipelines.append(pipeline)
        return FakeAsyncCursor(self.aggregate_result)

    def find(self, _filter):
        self.find_filter = _filter
        return FakeAsyncCursor(self.find_result)

    async def list_search_indexes(self):
        return FakeAsyncCursor(self.indexes)

    async def create_search_index(self, model):
        self.indexes.append({"name": model["name"], "model": model})


class _FakeDB:
    def __init__(self, col: FakeCollection):
        self._col = col

    def __getitem__(self, _name):
        return self._col


class FakeClient:
    def __init__(self, col: FakeCollection):
        self._col = col

    def __getitem__(self, _name):
        return _FakeDB(self._col)

    async def close(self):
        pass


@pytest.fixture
def col() -> FakeCollection:
    return FakeCollection()


@pytest.fixture
def store(col: FakeCollection) -> AtlasMemoryStore:
    return AtlasMemoryStore(
        embeddings=FakeEmbeddings(),
        user_id="tester",
        client=FakeClient(col),
    )


async def test_remember_embeds_and_inserts(
    store: AtlasMemoryStore, col: FakeCollection
):
    doc_id = await store.remember("user likes tea", role="user")
    assert doc_id
    doc = col.inserted[0]
    assert doc["content"] == "user likes tea"
    assert doc["user_id"] == "tester"
    assert doc["role"] == "user"
    assert doc["embedding"] == [14.0, 1.0, 0.0]


async def test_recall_vector_pipeline(store: AtlasMemoryStore, col: FakeCollection):
    col.aggregate_result = [{"_id": "a", "content": "tea"}]
    results = await store.recall("drinks", method="vector")
    assert results == ["tea"]

    stage = col.pipelines[0][0]["$vectorSearch"]
    assert stage["index"] == VECTOR_INDEX
    assert stage["path"] == "embedding"
    assert stage["filter"] == {"user_id": "tester"}
    assert stage["numCandidates"] == 50


async def test_recall_text_pipeline(store: AtlasMemoryStore, col: FakeCollection):
    col.aggregate_result = [{"_id": "a", "content": "tea"}]
    results = await store.recall("drinks", method="text")
    assert results == ["tea"]
    assert "$search" in col.pipelines[0][0]
    assert col.pipelines[0][1] == {"$match": {"user_id": "tester"}}


async def test_hybrid_rrf_merges_rankings(store: AtlasMemoryStore, monkeypatch):
    async def fake_vector(_q, _n):
        return [{"_id": "a", "content": "A"}, {"_id": "b", "content": "B"}]

    async def fake_text(_q, _n):
        return [{"_id": "b", "content": "B"}, {"_id": "c", "content": "C"}]

    monkeypatch.setattr(store, "_vector", fake_vector)
    monkeypatch.setattr(store, "_text", fake_text)

    results = await store.recall("q", method="hybrid", top_k=3)
    # B ranks in both lists -> fused score beats A and C
    assert results[0] == "B"
    assert set(results) == {"A", "B", "C"}


async def test_profile_filters_by_kind(store: AtlasMemoryStore, col: FakeCollection):
    col.find_result = [{"content": "prefers dark mode"}]
    assert await store.profile() == ["prefers dark mode"]
    assert col.find_filter == {"user_id": "tester", "kind": "profile"}


async def test_ensure_indexes_creates_missing(
    store: AtlasMemoryStore, col: FakeCollection
):
    await store.ensure_indexes(dimensions=1024)
    names = {i["name"] for i in col.indexes}
    assert names == {"memory_vector_index", "memory_text_index"}

    # second call is a no-op
    await store.ensure_indexes(dimensions=1024)
    assert len(col.indexes) == 2


async def test_as_tools(store: AtlasMemoryStore, col: FakeCollection):
    tools = store.as_tools()
    assert {t.name for t in tools} == {"save_memory", "search_memory"}
    save, _search = tools
    assert await save.ainvoke({"content": "remember me"}) == "saved"
    assert col.inserted[0]["content"] == "remember me"
