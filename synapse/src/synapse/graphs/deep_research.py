"""Deep Research agent — map-reduce investigation with synthesis.

The flagship Synapse pattern:

1. **Planner** — decomposes a research question into focused sub-questions.
2. **Researchers** — a ReAct sub-agent per sub-question, fanned out in
   parallel via LangGraph's ``Send`` API; each investigates with tools
   (web search, MCP servers) and returns a cited brief.
3. **Synthesizer** — merges all briefs into one structured, cited report.

Parallelism is real: researchers run concurrently, and the platform traces
each as its own span tree in Langfuse.
"""

from __future__ import annotations

import operator
from typing import Annotated

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Send
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

PLANNER_PROMPT = (
    "You are a research planner. Break the research question into "
    "{max_questions} or fewer focused, non-overlapping sub-questions that "
    "together fully answer it. Each sub-question must be answerable "
    "independently with web-scale tools."
)

RESEARCHER_PROMPT = (
    "You are a research analyst. Investigate the assigned sub-question "
    "thoroughly with the tools available. Return a dense factual brief: "
    "key findings, concrete data points, and source URLs for every claim. "
    "No filler, no preamble."
)

SYNTHESIZER_PROMPT = (
    "You are a research synthesizer. Combine the analyst briefs into a "
    "single authoritative report answering the original question.\n"
    "Structure: executive summary, key findings (grouped by theme), "
    "contradictions or gaps, and a sources section. Preserve citations "
    "from the briefs. Do not invent facts."
)


class ResearchPlan(BaseModel):
    """Focused sub-questions derived from the research question."""

    questions: list[str] = Field(description="Independent sub-questions to research.")


class ResearchBrief(BaseModel):
    """One analyst's cited findings on a single sub-question."""

    question: str
    brief: str = Field(description="Dense findings with inline source URLs.")


class DeepResearchState(TypedDict):
    """State threaded through plan -> parallel research -> synthesize.

    ``messages`` makes the graph servable by ``AgentServer`` (the A2A
    contract is messages-in, messages-out); ``question`` may also be passed
    directly when invoking the graph programmatically.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    question: str
    sub_questions: list[str]
    briefs: Annotated[list[ResearchBrief], operator.add]
    report: str


def _question_from(state: DeepResearchState) -> str:
    """Research question: explicit ``question`` or the last human message."""
    if question := state.get("question"):
        return question
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            return message.text
    raise ValueError("deep research needs a question or a human message")


def create_deep_research_agent(
    model: BaseChatModel,
    tools: list[BaseTool],
    *,
    name: str | None = None,
    max_questions: int = 5,
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
) -> CompiledStateGraph:
    """Build a deep research graph with parallel analyst fan-out.

    Args:
        model: Chat model for planning, research, and synthesis.
        tools: Investigation tools for researchers (web search, MCP tools).
        name: Agent name for traces and the A2A agent card.
        max_questions: Upper bound on parallel research branches.
        checkpointer: Short-term memory (thread state). Omit for stateless.
        store: Long-term memory store available to tools at runtime.

    Returns:
        A compiled ``StateGraph``.
    """
    planner = model.with_structured_output(ResearchPlan)
    researcher = create_agent(model, tools, system_prompt=RESEARCHER_PROMPT)

    async def plan(state: DeepResearchState) -> dict:
        question = _question_from(state)
        result = await planner.ainvoke(
            [
                SystemMessage(
                    content=PLANNER_PROMPT.format(max_questions=max_questions)
                ),
                HumanMessage(content=question),
            ]
        )
        return {"question": question, "sub_questions": result.questions[:max_questions]}

    async def research(state: dict) -> dict:
        """One analyst branch. Receives ``{"question": ...}`` via Send."""
        result = await researcher.ainvoke(
            {"messages": [HumanMessage(content=state["question"])]}
        )
        return {
            "briefs": [
                ResearchBrief(
                    question=state["question"],
                    brief=result["messages"][-1].content,
                )
            ]
        }

    def fan_out(state: DeepResearchState) -> list[Send]:
        return [Send("research", {"question": q}) for q in state["sub_questions"]]

    async def synthesize(state: DeepResearchState) -> dict:
        briefs = "\n\n".join(
            f"### {brief.question}\n{brief.brief}" for brief in state["briefs"]
        )
        report = await model.ainvoke(
            [
                SystemMessage(content=SYNTHESIZER_PROMPT),
                HumanMessage(
                    content=(
                        f"Original question: {state['question']}\n\n"
                        f"Analyst briefs:\n{briefs}"
                    )
                ),
            ]
        )
        # A2A callers read the answer from messages; programmatic callers
        # may read the structured ``report`` field instead.
        return {
            "report": report.content,
            "messages": [AIMessage(content=report.content)],
        }

    graph = StateGraph(DeepResearchState)
    graph.add_node("plan", plan)
    graph.add_node("research", research)
    graph.add_node("synthesize", synthesize)

    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", fan_out, ["research"])
    graph.add_edge("research", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile(name=name, checkpointer=checkpointer, store=store)
