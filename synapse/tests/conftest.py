from __future__ import annotations

import pytest

from synapse.config import SynapseConfig


@pytest.fixture
def config() -> SynapseConfig:
    """Deterministic config, independent of the process environment."""
    return SynapseConfig(
        namespace="tenant-test",
        agent_name="test-agent",
        gateway_url="http://gateway.test",
        llm_backend="anthropic",
        llm_model="claude-test",
        evermemos_url="http://evermemos.test",
        memory_user_id="tester",
    )
