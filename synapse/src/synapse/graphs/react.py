"""ReAct agent — the foundational tool-calling loop.

Thin, opinionated wrapper over LangGraph's prebuilt ReAct agent that wires
in Synapse defaults: gateway-routed models, long-term memory, and tracing.
"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore


def create_react_agent(
    model: BaseChatModel,
    tools: list[BaseTool],
    *,
    prompt: str | None = None,
    name: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
    **model_kwargs: Any,
) -> CompiledStateGraph:
    """Build a ReAct agent graph.

    Args:
        model: Chat model — typically ``synapse.llm.GatewayChatModel`` so all
            LLM traffic flows through the platform gateway (credential
            injection, guardrails, tracing) instead of holding API keys.
        tools: Tools the agent may call — local tools or MCP tools loaded
            through the gateway via ``synapse.tools.load_mcp_tools``.
        prompt: Optional system prompt prepended to every conversation.
        name: Agent name, surfaced in traces and the A2A agent card.
        checkpointer: Short-term memory (thread state). Omit for stateless.
        store: Long-term memory store — typically
            ``synapse.memory.EverMemStore`` — available to tools at runtime.
        **model_kwargs: Forwarded to ``langchain.agents.create_agent``.

    Returns:
        A compiled ``StateGraph`` implementing the Reason-Act-Observe loop.
    """
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
        name=name,
        checkpointer=checkpointer,
        store=store,
        **model_kwargs,
    )
