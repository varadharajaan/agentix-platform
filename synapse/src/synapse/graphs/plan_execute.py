"""Plan-Execute agent — deliberate planning with replanning.

A three-phase graph for tasks too complex for a reactive loop:

1. **Planner** — decomposes the objective into an ordered step plan.
2. **Executor** — runs the current step with a tool-calling ReAct sub-agent.
3. **Replanner** — inspects results, updates the plan, or finishes.

The executor loops through the plan; the replanner adapts it after every
step, so the agent recovers from dead ends instead of committing to a
stale plan.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

PLANNER_PROMPT = (
    "You are a planning engine. Decompose the objective into the smallest "
    "sufficient ordered list of steps. Each step must be independently "
    "executable by an agent with tools. Do not number the steps — order is "
    "implied. Do not add a summary or conclusion step."
)

REPLANNER_PROMPT = (
    "You are a replanning engine. Given the objective, the original plan, "
    "the steps already completed, and their results, update the plan.\n"
    "- Remove completed steps.\n"
    "- Add, rewrite, or reorder remaining steps if results demand it.\n"
    "- If the objective is fully achieved, respond instead with the final "
    "answer to the user."
)


class Plan(BaseModel):
    """Ordered steps remaining to achieve the objective."""

    steps: list[str] = Field(
        description="Steps still to execute, in order. Must be empty when done."
    )


class FinalResponse(BaseModel):
    """Terminal answer returned when the objective is achieved."""

    response: str = Field(description="Complete final answer to the user.")


class ReplanDecision(BaseModel):
    """The replanner either continues with an updated plan or finishes."""

    action: Plan | FinalResponse = Field(
        description="Updated plan to continue, or the final response to finish."
    )


class PlanExecuteState(TypedDict):
    """Graph state threaded through planner, executor, and replanner."""

    input: str
    plan: list[str]
    past_steps: Annotated[list[tuple[str, str]], operator.add]
    messages: Annotated[list[BaseMessage], add_messages]
    response: str


def create_plan_execute_agent(
    model: BaseChatModel,
    tools: list[BaseTool],
    *,
    name: str | None = None,
    max_cycles: int = 12,
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
) -> CompiledStateGraph:
    """Build a Plan-Execute-Replanner graph.

    Args:
        model: Chat model for planning and replanning (structured output).
        tools: Tools available to the executor sub-agent.
        name: Agent name for traces and the A2A agent card.
        max_cycles: Safety bound on plan-execute-replan iterations.
        checkpointer: Short-term memory (thread state). Omit for stateless.
        store: Long-term memory store available to tools at runtime.

    Returns:
        A compiled ``StateGraph``.
    """
    planner_model = model.with_structured_output(Plan)
    replanner_model = model.with_structured_output(ReplanDecision)
    executor = create_agent(model, tools)

    async def plan_step(state: PlanExecuteState) -> dict:
        plan = await planner_model.ainvoke(
            [
                SystemMessage(content=PLANNER_PROMPT),
                HumanMessage(content=state["input"]),
            ]
        )
        return {"plan": plan.steps}

    async def execute_step(state: PlanExecuteState) -> dict:
        step = state["plan"][0]
        task = (
            f"Objective: {state['input']}\n\n"
            f"Execute exactly this step and report the result:\n{step}"
        )
        result = await executor.ainvoke({"messages": [HumanMessage(content=task)]})
        report = result["messages"][-1].content
        return {
            "plan": state["plan"][1:],
            "past_steps": [(step, report)],
        }

    async def replan_step(state: PlanExecuteState) -> dict:
        history = "\n".join(
            f"- {step}: {result}" for step, result in state["past_steps"]
        )
        decision = await replanner_model.ainvoke(
            [
                SystemMessage(content=REPLANNER_PROMPT),
                HumanMessage(
                    content=(
                        f"Objective: {state['input']}\n\n"
                        f"Original plan: {state['plan']}\n\n"
                        f"Completed so far:\n{history or '(nothing yet)'}"
                    )
                ),
            ]
        )
        if isinstance(decision.action, FinalResponse):
            return {"response": decision.action.response}
        return {"plan": decision.action.steps}

    def route_after_replan(state: PlanExecuteState) -> Literal["execute", "__end__"]:
        if state.get("response"):
            return END
        if not state.get("plan"):
            return END
        return "execute"

    def route_after_execute(state: PlanExecuteState) -> Literal["replan", "__end__"]:
        if len(state["past_steps"]) >= max_cycles:
            return END
        return "replan"

    graph = StateGraph(PlanExecuteState)
    graph.add_node("plan", plan_step)
    graph.add_node("execute", execute_step)
    graph.add_node("replan", replan_step)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute")
    graph.add_conditional_edges("execute", route_after_execute)
    graph.add_conditional_edges("replan", route_after_replan)

    return graph.compile(name=name, checkpointer=checkpointer, store=store)
