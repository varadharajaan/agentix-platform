"""Supervisor agent — hierarchical multi-agent orchestration.

A supervisor model coordinates a team of named worker agents. On every
turn it inspects the conversation and either delegates to one worker or
finishes. Workers are themselves compiled graphs (ReAct, Plan-Execute,
deep research — any Synapse template composes).
"""

from __future__ import annotations

from typing import Annotated, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

SUPERVISOR_PROMPT = (
    "You are a supervisor coordinating a team of specialist agents.\n"
    "Team roster:\n{roster}\n\n"
    "Rules:\n"
    "- Delegate one sub-task at a time to the best-suited worker.\n"
    "- Never answer from your own knowledge when a worker can act.\n"
    "- When the user's request is fully satisfied, choose FINISH and write "
    "the final consolidated answer."
)


class SupervisorState(TypedDict):
    """Shared conversation state between supervisor and workers."""

    messages: Annotated[list[BaseMessage], add_messages]
    next: str


def create_supervisor_agent(
    model: BaseChatModel,
    workers: dict[str, CompiledStateGraph],
    *,
    worker_descriptions: dict[str, str] | None = None,
    name: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
) -> CompiledStateGraph:
    """Build a supervisor graph routing among worker graphs.

    Args:
        model: Chat model used for routing decisions (structured output).
        workers: Map of worker name -> compiled graph. Each worker must
            accept and return a ``messages`` list (all Synapse templates do).
        worker_descriptions: Optional human-readable capability summaries
            shown to the supervisor; defaults to the worker names.
        name: Agent name for traces and the A2A agent card.
        checkpointer: Short-term memory (thread state). Omit for stateless.
        store: Long-term memory store available to tools at runtime.

    Returns:
        A compiled ``StateGraph``.
    """
    if not workers:
        raise ValueError("supervisor needs at least one worker")

    roster = {
        w: (worker_descriptions or {}).get(w, w.replace("_", " ")) for w in workers
    }
    options = (*tuple(roster), "FINISH")

    class Route(BaseModel):
        next: Literal[options] = Field(  # type: ignore[valid-type]
            description="Worker to delegate to, or FINISH when done."
        )
        instruction: str = Field(
            default="",
            description="Specific sub-task handed to the chosen worker.",
        )
        final_answer: str = Field(
            default="", description="Consolidated answer; required when next=FINISH."
        )

    router = model.with_structured_output(Route)
    roster_text = "\n".join(f"- {w}: {desc}" for w, desc in roster.items())
    system = SystemMessage(content=SUPERVISOR_PROMPT.format(roster=roster_text))

    async def supervise(state: SupervisorState) -> dict:
        decision = await router.ainvoke([system, *state["messages"]])
        if decision.next == "FINISH":
            return {
                "next": "FINISH",
                "messages": [HumanMessage(content=decision.final_answer)],
            }
        handoff = decision.instruction or state["messages"][-1].content
        return {"next": decision.next, "messages": [HumanMessage(content=handoff)]}

    def make_worker_node(worker: CompiledStateGraph):
        async def run_worker(state: SupervisorState) -> dict:
            result = await worker.ainvoke({"messages": state["messages"]})
            return {"messages": [result["messages"][-1]]}

        return run_worker

    def route(state: SupervisorState) -> str:
        return END if state["next"] == "FINISH" else state["next"]

    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervise)
    for worker_name, worker in workers.items():
        graph.add_node(worker_name, make_worker_node(worker))
        graph.add_edge(worker_name, "supervisor")

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route)

    return graph.compile(name=name, checkpointer=checkpointer, store=store)
