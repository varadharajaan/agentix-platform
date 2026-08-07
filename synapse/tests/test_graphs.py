"""Graph template tests — structure and a live ReAct run with a fake model."""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage

from synapse.graphs import (
    create_deep_research_agent,
    create_plan_execute_agent,
    create_react_agent,
    create_supervisor_agent,
)


class FakeModel(FakeListChatModel):
    """A fake chat model that tolerates tool binding."""

    def bind_tools(self, tools, **kwargs):
        return self


def test_react_agent_runs_to_completion():
    graph = create_react_agent(model=FakeModel(responses=["final answer"]), tools=[])
    result = graph.invoke({"messages": [HumanMessage(content="hi")]})
    assert result["messages"][-1].content == "final answer"


def test_plan_execute_structure():
    graph = create_plan_execute_agent(model=FakeModel(responses=["x"]), tools=[])
    nodes = set(graph.get_graph().nodes)
    assert {"plan", "execute", "replan"} <= nodes


def test_supervisor_structure_and_routes():
    worker = create_react_agent(model=FakeModel(responses=["w"]), tools=[])
    graph = create_supervisor_agent(
        model=FakeModel(responses=["x"]),
        workers={"researcher": worker, "writer": worker},
    )
    nodes = set(graph.get_graph().nodes)
    assert {"supervisor", "researcher", "writer"} <= nodes


def test_supervisor_requires_workers():
    with pytest.raises(ValueError, match="at least one worker"):
        create_supervisor_agent(model=FakeModel(responses=["x"]), workers={})


def test_deep_research_structure():
    graph = create_deep_research_agent(model=FakeModel(responses=["x"]), tools=[])
    nodes = set(graph.get_graph().nodes)
    assert {"plan", "research", "synthesize"} <= nodes


class FakePlannerModel(FakeModel):
    """Fake model whose structured-output call yields a fixed plan."""

    def with_structured_output(self, schema, **kwargs):
        from langchain_core.runnables import RunnableLambda

        return RunnableLambda(lambda _msgs: schema(questions=["q1", "q2"]))


async def test_deep_research_runs_end_to_end_from_messages():
    """The A2A contract: messages in, answer in the final message."""
    graph = create_deep_research_agent(
        model=FakePlannerModel(responses=["x"]), tools=[]
    )
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="research topic")]}
    )
    assert result["question"] == "research topic"
    assert len(result["briefs"]) == 2
    assert result["messages"][-1].content == result["report"]


async def test_deep_research_accepts_explicit_question():
    graph = create_deep_research_agent(
        model=FakePlannerModel(responses=["x"]), tools=[]
    )
    result = await graph.ainvoke({"question": "direct question", "messages": []})
    assert result["question"] == "direct question"
    assert len(result["briefs"]) == 2
