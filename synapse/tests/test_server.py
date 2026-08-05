import json
from typing import Annotated

import httpx
import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from synapse.runtime import AgentServer
from synapse.runtime.server import AgentCard, Skill


class EchoState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def _echo(state: EchoState):
    return {"messages": [AIMessage(content="pong")]}


def _echo_graph():
    graph = StateGraph(EchoState)
    graph.add_node("echo", _echo)
    graph.add_edge(START, "echo")
    graph.add_edge("echo", END)
    return graph.compile(name="echo")


@pytest.fixture
def server() -> AgentServer:
    return AgentServer(
        _echo_graph(),
        AgentCard(
            name="echo",
            description="test echo agent",
            skills=[Skill(id="echo", name="Echo", description="replies pong")],
        ),
    )


@pytest.fixture
async def client(server: AgentServer):
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_agent_card(client: httpx.AsyncClient):
    resp = await client.get("/.well-known/agent.json")
    assert resp.status_code == 200
    card = resp.json()
    assert card["name"] == "echo"
    assert card["capabilities"]["streaming"] is True
    assert card["skills"][0]["id"] == "echo"


async def test_healthz(client: httpx.AsyncClient):
    resp = await client.get("/healthz")
    assert resp.json() == {"status": "ok", "agent": "echo"}


async def test_tasks_send_completes_with_artifact(client: httpx.AsyncClient):
    resp = await client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "ping"}],
                }
            },
        },
    )
    body = resp.json()
    assert body["id"] == 7
    task = body["result"]
    assert task["status"]["state"] == "completed"
    assert task["artifacts"][0]["parts"][0]["text"] == "pong"


async def test_unknown_method_returns_jsonrpc_error(client: httpx.AsyncClient):
    resp = await client.post(
        "/", json={"jsonrpc": "2.0", "id": 1, "method": "nope"}
    )
    assert resp.json()["error"]["code"] == -32601


async def test_send_subscribe_streams_lifecycle(client: httpx.AsyncClient):
    async with client.stream(
        "POST",
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tasks/sendSubscribe",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "ping"}],
                }
            },
        },
    ) as resp:
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    states = [e.get("status", {}).get("state") for e in events if "status" in e]
    assert states[0] == "submitted"
    assert "working" in states
    assert states[-1] == "completed"
