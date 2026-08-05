"""Deep Research agent — the flagship Synapse workload.

A LangGraph deep-research graph (plan → parallel analysts → synthesis)
that:

- calls its LLM through the platform gateway (no API keys in the pod),
- searches the web through an MCP tool server (no tool credentials either),
- remembers findings in MongoDB Atlas Vector Search (or EverMemOS),
- traces every span to LangSmith / Phoenix / Langfuse,
- serves A2A so any other platform agent can invoke it.

Run locally:   python agent.py
Deploy:        synapse export agent:graph --image <ecr>/deep-research:v1 \
                   --namespace tenant-alpha -o manifests.yaml
"""

from __future__ import annotations

import asyncio
import os

from synapse import AgentCard, AgentServer, EverMemStore, GatewayChatModel, Skill
from synapse.constants import DEFAULT_EMBEDDINGS_MODEL, DEFAULT_PORT
from synapse.graphs import create_deep_research_agent
from synapse.memory import MemoryStore
from synapse.tools import load_mcp_tools


def build_memory() -> MemoryStore | None:
    """Memory backend: atlas (default w/ URI), evermem, or none (local dev).

    ``SYNAPSE_MEMORY_BACKEND=none`` disables memory tools entirely — the
    right choice for a laptop run where neither Atlas nor EverMemOS is
    reachable.
    """
    backend = os.environ.get("SYNAPSE_MEMORY_BACKEND", "").lower()
    if backend == "none":
        return None
    uri = os.environ.get("SYNAPSE_MONGODB_URI")
    if backend == "atlas" or (uri and backend != "evermem"):
        from langchain_voyageai import VoyageAIEmbeddings

        from synapse.memory import AtlasMemoryStore

        return AtlasMemoryStore(
            connection_string=uri,
            embeddings=VoyageAIEmbeddings(model=DEFAULT_EMBEDDINGS_MODEL),
            user_id=os.environ.get("MEMORY_USER_ID", "deep-research"),
        )
    return EverMemStore(group_id="deep-research")


async def build_graph():
    """Assemble the graph with platform-wired dependencies."""
    model = GatewayChatModel(temperature=0.2)

    tools = []
    if os.environ.get("SYNAPSE_SEARCH_SERVER"):
        # MCP search server (e.g. Tavily/Brave) exposed via the gateway.
        tools.extend(await load_mcp_tools(os.environ["SYNAPSE_SEARCH_SERVER"]))

    if memory := build_memory():
        tools.extend(memory.as_tools())

    return create_deep_research_agent(
        model=model,
        tools=tools,
        name="deep-research",
        max_questions=int(os.environ.get("SYNAPSE_MAX_QUESTIONS", "5")),
    )


def build_card() -> AgentCard:
    return AgentCard(
        name="deep-research",
        description=(
            "Decomposes research questions, investigates in parallel, and "
            "returns a cited synthesis."
        ),
        version="0.1.0",
        skills=[
            Skill(
                id="deep-research",
                name="Deep Research",
                description="Multi-source investigation with a cited report",
                tags=["research", "synthesis", "citations"],
            )
        ],
    )


def main() -> None:
    # build_graph() is async (MCP tool discovery); run() is the blocking sync
    # entrypoint — uvicorn manages its own event loop.
    graph = asyncio.run(build_graph())
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    AgentServer(graph, build_card()).run(port=port)


if __name__ == "__main__":
    main()
