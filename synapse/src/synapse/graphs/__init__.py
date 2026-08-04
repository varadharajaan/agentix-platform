"""Production-grade LangGraph agent templates.

Each factory returns a compiled ``StateGraph`` ready to serve through the
Synapse runtime or export as a platform Agent manifest.
"""

from synapse.graphs.deep_research import create_deep_research_agent
from synapse.graphs.plan_execute import create_plan_execute_agent
from synapse.graphs.react import create_react_agent
from synapse.graphs.supervisor import create_supervisor_agent

__all__ = [
    "create_deep_research_agent",
    "create_plan_execute_agent",
    "create_react_agent",
    "create_supervisor_agent",
]
