"""Synapse — the LangGraph-native orchestration layer for Agentix Platform.

Author agents as LangGraph graphs; run them anywhere; deploy them to the
platform as first-class, mesh-enrolled, gateway-governed agents.
"""

from synapse.config import SynapseConfig, get_config
from synapse.llm import GatewayChatModel
from synapse.memory import EverMemStore
from synapse.runtime import AgentServer
from synapse.runtime.server import AgentCard, Skill

__version__ = "0.1.0"

__all__ = [
    "AgentCard",
    "AgentServer",
    "EverMemStore",
    "GatewayChatModel",
    "Skill",
    "SynapseConfig",
    "__version__",
    "get_config",
]
