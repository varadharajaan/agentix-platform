from synapse.config import SynapseConfig


def test_llm_base_url_targets_gateway_llm_path(config: SynapseConfig):
    assert (
        config.llm_base_url
        == "http://gateway.test/llm/tenant-test/anthropic/v1"
    )


def test_mcp_url_defaults_to_own_namespace(config: SynapseConfig):
    assert config.mcp_url("search") == "http://gateway.test/mcp/tenant-test/search"


def test_mcp_url_namespace_override(config: SynapseConfig):
    assert (
        config.mcp_url("agents", namespace="kagent-system")
        == "http://gateway.test/mcp/kagent-system/agents"
    )


def test_a2a_url(config: SynapseConfig):
    assert (
        config.a2a_url("tenant-beta", "deep-research")
        == "http://gateway.test/a2a/tenant-beta/deep-research"
    )


def test_keycloak_token_url(config: SynapseConfig):
    assert config.keycloak_token_url.endswith(
        "/realms/agents/protocol/openid-connect/token"
    )
