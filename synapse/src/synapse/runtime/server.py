"""A2A protocol server — expose any compiled graph as a platform agent.

The platform discovers and routes to agents over the A2A (Agent2Agent)
protocol: an agent card at ``/.well-known/agent.json`` and JSON-RPC
``tasks/send`` + ``tasks/sendSubscribe`` endpoints. ``AgentServer`` wraps
any compiled LangGraph graph with a compliant FastAPI surface, so a graph
built locally is deployable to the platform with zero protocol work.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from synapse.constants import (
    A2A_PROTOCOL_VERSION,
    DEFAULT_HOST,
    DEFAULT_PORT,
)

A2A_VERSION = A2A_PROTOCOL_VERSION  # backwards-compatible alias


class Skill(BaseModel):
    """One advertised capability in the agent card."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)


class AgentCard(BaseModel):
    """A2A discovery document served at ``/.well-known/agent.json``."""

    name: str
    description: str
    url: str = ""
    version: str = "0.1.0"
    protocol_version: str = A2A_VERSION
    capabilities: dict[str, bool] = Field(
        default_factory=lambda: {"streaming": True, "pushNotifications": False}
    )
    skills: list[Skill] = Field(default_factory=list)
    default_input_modes: list[str] = ["text"]
    default_output_modes: list[str] = ["text"]


def _jsonrpc_ok(request_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _extract_text(message: dict[str, Any]) -> str:
    """Pull concatenated text parts out of an A2A message."""
    return "\n".join(
        part.get("text", "")
        for part in message.get("parts", [])
        if part.get("type") == "text" or part.get("kind") == "text"
    )


def _task(task_id: str, state: str, text: str | None = None) -> dict[str, Any]:
    task: dict[str, Any] = {"id": task_id, "status": {"state": state}}
    if text is not None:
        task["artifacts"] = [
            {"artifactId": str(uuid.uuid4()), "parts": [{"type": "text", "text": text}]}
        ]
    return task


class AgentServer:
    """Serve a compiled LangGraph graph over the A2A protocol.

    Args:
        graph: Any compiled ``StateGraph`` that consumes and returns a
            ``messages`` list (all Synapse templates do).
        card: Discovery metadata for this agent.
    """

    def __init__(self, graph: CompiledStateGraph, card: AgentCard) -> None:
        self.graph = graph
        self.card = card
        self.app = FastAPI(title=card.name, version=card.version)
        self._routes()

    def _routes(self) -> None:
        @self.app.get("/.well-known/agent.json")
        async def agent_card() -> dict:
            return self.card.model_dump(by_alias=True)

        @self.app.get("/healthz")
        async def healthz() -> dict:
            return {"status": "ok", "agent": self.card.name}

        @self.app.post("/")
        async def rpc(request: Request) -> Any:
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(_jsonrpc_error(None, -32700, "Parse error"))

            method = body.get("method")
            request_id = body.get("id")
            params = body.get("params") or {}

            if method == "tasks/send":
                return JSONResponse(await self._send(request_id, params))
            if method == "tasks/sendSubscribe":
                return StreamingResponse(
                    self._send_subscribe(params),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache"},
                )
            return JSONResponse(
                _jsonrpc_error(request_id, -32601, f"Method not found: {method}")
            )

    async def _invoke(self, params: dict[str, Any]) -> str:
        text = _extract_text(params.get("message") or {})
        config = {"configurable": {"thread_id": params.get("id") or str(uuid.uuid4())}}
        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=text)]}, config=config
        )
        return result["messages"][-1].content

    async def _send(self, request_id: Any, params: dict[str, Any]) -> dict:
        task_id = params.get("id") or str(uuid.uuid4())
        try:
            answer = await self._invoke(params)
        except Exception as exc:  # surfaced to caller as a failed task
            return _jsonrpc_ok(request_id, _task(task_id, "failed", str(exc)))
        return _jsonrpc_ok(request_id, _task(task_id, "completed", answer))

    async def _send_subscribe(self, params: dict[str, Any]) -> AsyncIterator[str]:
        task_id = params.get("id") or str(uuid.uuid4())

        def sse(event: dict[str, Any]) -> str:
            return f"data: {json.dumps(event)}\n\n"

        yield sse(_task(task_id, "submitted"))
        yield sse(_task(task_id, "working"))

        text = _extract_text(params.get("message") or {})
        config = {"configurable": {"thread_id": task_id}}
        final = ""
        try:
            async for chunk, _meta in self.graph.astream(
                {"messages": [HumanMessage(content=text)]},
                config=config,
                stream_mode="messages",
            ):
                if chunk.content:
                    final += chunk.content
                    yield sse(
                        {
                            "id": task_id,
                            "artifact": {
                                "parts": [{"type": "text", "text": chunk.content}]
                            },
                            "append": True,
                        }
                    )
            yield sse(_task(task_id, "completed"))
        except Exception as exc:
            yield sse(_task(task_id, "failed", str(exc)))

    def run(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        """Serve forever — the container entrypoint.

        Blocking; call from synchronous code (uvicorn creates its own event
        loop, so this cannot be called from inside ``asyncio.run()``).
        """
        import uvicorn

        uvicorn.run(self.app, host=host, port=port)
