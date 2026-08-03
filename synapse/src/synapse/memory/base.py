"""Pluggable long-term memory interface.

Synapse agents take any ``MemoryStore`` — the platform ships two:

- ``AtlasMemoryStore`` (default) — MongoDB Atlas Vector Search; one store
  for documents, vectors, and sessions.
- ``EverMemStore`` — the platform's paved-road EverMemOS service.

Bring your own by implementing ``remember`` / ``recall`` / ``profile``;
``MemoryTools`` gives any implementation LangChain tool bindings for free.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from langchain_core.tools import tool


@runtime_checkable
class MemoryStore(Protocol):
    """Structural contract every Synapse memory backend satisfies."""

    async def remember(self, content: str, *, role: str = "assistant") -> None:
        """Persist one memory item."""
        ...

    async def recall(self, query: str, *, top_k: int = 5) -> list[str]:
        """Return the most relevant memories for ``query``."""
        ...

    async def profile(self) -> list[str]:
        """Return profile-type memories for the current identity."""
        ...


class MemoryTools:
    """Adapt any ``MemoryStore`` into LangChain tools an agent can call."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def as_tools(self) -> list[Any]:
        store = self.store

        @tool
        async def save_memory(content: str) -> str:
            """Save an important fact, preference, or event to long-term memory."""
            await store.remember(content, role="assistant")
            return "saved"

        @tool
        async def search_memory(query: str) -> str:
            """Search long-term memory for facts relevant to the query."""
            results = await store.recall(query)
            return "\n".join(results) if results else "no relevant memories"

        return [save_memory, search_memory]
