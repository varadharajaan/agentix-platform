"""MongoDB Atlas Vector Search memory — the Synapse default.

One store replaces the classic four-store memory stack: documents,
vector embeddings, and session state all live in a single Atlas
collection, searched with ``$vectorSearch`` (semantic), ``$search``
(lexical), or client-side reciprocal-rank-fusion of the two (hybrid).

Embeddings are pluggable — pass any LangChain ``Embeddings`` model.
Voyage AI (MongoDB's embedding models) is the natural pairing:

    from langchain_voyageai import VoyageAIEmbeddings
    store = AtlasMemoryStore(
        connection_string=os.environ["SYNAPSE_MONGODB_URI"],
        embeddings=VoyageAIEmbeddings(model="voyage-3-large"),
        user_id="agent",
    )
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from langchain_core.embeddings import Embeddings

from synapse.constants import (
    ATLAS_DEFAULT_COLLECTION,
    ATLAS_DEFAULT_DATABASE,
    ATLAS_DEFAULT_DIMENSIONS,
    ATLAS_RRF_K,
    ATLAS_TEXT_INDEX,
    ATLAS_VECTOR_INDEX,
)
from synapse.memory.base import MemoryTools

RecallMethod = Literal["vector", "text", "hybrid"]

VECTOR_INDEX = ATLAS_VECTOR_INDEX  # canonical name lives in synapse.constants
TEXT_INDEX = ATLAS_TEXT_INDEX


class AtlasMemoryStore:
    """Long-term agent memory on MongoDB Atlas.

    Args:
        connection_string: Atlas (or local MongoDB) connection URI.
        embeddings: LangChain embeddings model used for writes and
            vector recall.
        user_id: Identity memories are stored under.
        database: Database name.
        collection: Collection name.
    """

    def __init__(
        self,
        connection_string: str | None = None,
        embeddings: Embeddings | None = None,
        *,
        user_id: str,
        database: str = ATLAS_DEFAULT_DATABASE,
        collection: str = ATLAS_DEFAULT_COLLECTION,
        client: Any | None = None,
    ) -> None:
        if client is None:
            if not connection_string:
                raise ValueError("connection_string is required when client is omitted")
            try:
                from pymongo.asynchronous.mongo_client import AsyncMongoClient
            except ImportError as exc:
                raise ImportError(
                    "pymongo is not installed — add the extra: "
                    "pip install 'synapse-agentic[atlas]'"
                ) from exc
            client = AsyncMongoClient(connection_string)
        self._embeddings = embeddings
        self.user_id = user_id
        self._client = client
        self._col = client[database][collection]

    async def ensure_indexes(
        self, *, dimensions: int = ATLAS_DEFAULT_DIMENSIONS
    ) -> None:
        """Create the Atlas Search indexes (idempotent)."""
        existing = {
            idx["name"] async for idx in await self._col.list_search_indexes()
        }
        if VECTOR_INDEX not in existing:
            await self._col.create_search_index(
                {
                    "name": VECTOR_INDEX,
                    "type": "vectorSearch",
                    "definition": {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embedding",
                                "numDimensions": dimensions,
                                "similarity": "cosine",
                            },
                            {"type": "filter", "path": "user_id"},
                        ]
                    },
                }
            )
        if TEXT_INDEX not in existing:
            await self._col.create_search_index(
                {
                    "name": TEXT_INDEX,
                    "type": "search",
                    "definition": {
                        "mappings": {
                            "dynamic": False,
                            "fields": {"content": {"type": "string"}},
                        }
                    },
                }
            )

    async def remember(
        self,
        content: str,
        *,
        role: str = "assistant",
        kind: str = "episodic",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Embed and persist one memory item; returns its id."""
        vector = await self._embeddings.aembed_query(content)
        doc = {
            "_id": uuid.uuid4().hex,
            "user_id": self.user_id,
            "content": content,
            "role": role,
            "kind": kind,
            "metadata": metadata or {},
            "embedding": vector,
            "created_at": int(time.time() * 1000),
        }
        await self._col.insert_one(doc)
        return doc["_id"]

    async def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        method: RecallMethod = "hybrid",
    ) -> list[str]:
        """Search memories: ``vector``, ``text``, or ``hybrid`` (RRF)."""
        if method == "vector":
            return [doc["content"] for doc in await self._vector(query, top_k)]
        if method == "text":
            return [doc["content"] for doc in await self._text(query, top_k)]
        return [doc["content"] for doc in await self._hybrid(query, top_k)]

    async def profile(self, *, limit: int = 10) -> list[str]:
        """Profile-type memories for this identity, newest first."""
        cursor = (
            self._col.find({"user_id": self.user_id, "kind": "profile"})
            .sort("created_at", -1)
            .limit(limit)
        )
        return [doc["content"] async for doc in cursor]

    def as_tools(self) -> list[Any]:
        """LangChain tools (``save_memory`` / ``search_memory``)."""
        return MemoryTools(self).as_tools()

    async def aclose(self) -> None:
        await self._client.close()

    # -- retrieval internals -------------------------------------------------

    async def _vector(self, query: str, limit: int) -> list[dict]:
        vector = await self._embeddings.aembed_query(query)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": VECTOR_INDEX,
                    "path": "embedding",
                    "queryVector": vector,
                    "numCandidates": limit * 10,
                    "limit": limit,
                    "filter": {"user_id": self.user_id},
                }
            },
            {"$project": {"content": 1, "_id": 1}},
        ]
        return [doc async for doc in await self._col.aggregate(pipeline)]

    async def _text(self, query: str, limit: int) -> list[dict]:
        pipeline = [
            {
                "$search": {
                    "index": TEXT_INDEX,
                    "text": {"query": query, "path": "content"},
                }
            },
            {"$match": {"user_id": self.user_id}},
            {"$limit": limit},
            {"$project": {"content": 1, "_id": 1}},
        ]
        return [doc async for doc in await self._col.aggregate(pipeline)]

    async def _hybrid(
        self, query: str, limit: int, *, rrf_k: int = ATLAS_RRF_K
    ) -> list[dict]:
        """Reciprocal rank fusion over vector + text rankings."""
        vector_hits, text_hits = await self._vector(query, limit * 2), await self._text(
            query, limit * 2
        )
        scores: dict[str, float] = {}
        docs: dict[str, dict] = {}
        for hits in (vector_hits, text_hits):
            for rank, doc in enumerate(hits):
                doc_id = doc["_id"]
                docs[doc_id] = doc
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
        ranked = sorted(scores, key=scores.__getitem__, reverse=True)
        return [docs[doc_id] for doc_id in ranked[:limit]]
