"""EverMemOS long-term memory client.

EverMemOS gives agents durable, hybrid-searchable memory (BM25 + vector +
reranker) backed by MongoDB, Elasticsearch, and Milvus. ``EverMemStore``
wraps its REST API and exposes two integration styles:

- direct calls — ``await store.remember(...)`` / ``await store.recall(...)``
- as LangChain tools — ``store.as_tools()`` hands any Synapse graph
  ``save_memory`` / ``search_memory`` tools it can call autonomously.

Note the search endpoint is ``GET`` with a JSON body (an EverMemOS
convention); httpx supports this via ``client.request``.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

import httpx

from synapse.config import SynapseConfig, get_config
from synapse.constants import (
    DEFAULT_MEMORY_TYPES,
    EVERMEM_API_CONVERSATION_META,
    EVERMEM_API_MEMORIES,
    EVERMEM_API_SEARCH,
    EVERMEM_HEALTH_PATH,
    EVERMEM_TIMEOUT_S,
)
from synapse.memory.base import MemoryTools

RetrieveMethod = Literal["keyword", "vector", "hybrid", "rrf", "agentic"]

__all__ = ["DEFAULT_MEMORY_TYPES", "EverMemStore", "RetrieveMethod"]


class EverMemStore:
    """Async client for the platform's shared EverMemOS memory service.

    Args:
        config: Platform configuration; defaults to the process environment.
        user_id: Identity memories are stored under; defaults to the
            configured ``memory_user_id``.
        group_id: Optional conversation/group scope for memories.
    """

    def __init__(
        self,
        config: SynapseConfig | None = None,
        *,
        user_id: str | None = None,
        group_id: str | None = None,
    ) -> None:
        cfg = config or get_config()
        self.user_id = user_id or cfg.memory_user_id
        self.group_id = group_id
        self._client = httpx.AsyncClient(
            base_url=cfg.evermemos_url, timeout=EVERMEM_TIMEOUT_S
        )

    async def health(self) -> bool:
        """True when EverMemOS is reachable."""
        try:
            resp = await self._client.get(EVERMEM_HEALTH_PATH)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def ensure_group(self, description: str = "Synapse agent memory") -> None:
        """Register the conversation group (idempotent)."""
        if not self.group_id:
            return
        await self._client.post(
            EVERMEM_API_CONVERSATION_META,
            json={
                "scene": "group_chat",
                "scene_desc": {"description": description},
                "name": self.group_id,
                "group_id": self.group_id,
                "created_at": _epoch_ms(),
                "user_details": {
                    self.user_id: {"full_name": self.user_id, "role": "user"}
                },
            },
        )

    async def remember(
        self,
        content: str,
        *,
        role: Literal["user", "assistant"] = "assistant",
        sender: str | None = None,
    ) -> None:
        """Persist one memory item."""
        await self._client.post(
            EVERMEM_API_MEMORIES,
            json={
                "group_id": self.group_id,
                "message_id": uuid.uuid4().hex,
                "create_time": _epoch_ms(),
                "sender": sender or self.user_id,
                "sender_name": sender or self.user_id,
                "role": role,
                "content": content,
            },
        )

    async def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        method: RetrieveMethod = "hybrid",
        memory_types: list[str] | None = None,
    ) -> list[str]:
        """Hybrid-search memories relevant to ``query``.

        Returns memory contents, most relevant first. EverMemOS has
        historically returned the text under either ``memory_content`` or
        ``content`` — both are accepted.
        """
        resp = await self._client.request(
            "GET",
            EVERMEM_API_SEARCH,
            json={
                "query": query,
                "retrieve_method": method,
                "top_k": top_k,
                "memory_types": memory_types or DEFAULT_MEMORY_TYPES,
                "user_id": self.user_id,
                "group_id": self.group_id,
            },
        )
        resp.raise_for_status()
        memories = resp.json().get("data", {}).get("memories", [])
        return [
            m.get("memory_content") or m.get("content", "")
            for m in memories
            if isinstance(m, dict)
        ]

    async def profile(self, *, page_size: int = 10) -> list[str]:
        """Fetch the stored profile for this user."""
        resp = await self._client.request(
            "GET",
            EVERMEM_API_MEMORIES,
            json={
                "user_id": self.user_id,
                "memory_type": "profile",
                "page": 1,
                "page_size": page_size,
            },
        )
        resp.raise_for_status()
        memories = resp.json().get("data", {}).get("memories", [])
        return [
            m.get("memory_content") or m.get("content", "")
            for m in memories
            if isinstance(m, dict)
        ]

    def as_tools(self) -> list[Any]:
        """LangChain tools (``save_memory`` / ``search_memory``)."""
        return MemoryTools(self).as_tools()

    async def aclose(self) -> None:
        await self._client.aclose()


def _epoch_ms() -> int:
    return int(time.time() * 1000)
