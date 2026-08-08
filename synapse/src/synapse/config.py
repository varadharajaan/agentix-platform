"""Runtime configuration for Synapse agents.

Everything is environment-driven so the same artifact runs unmodified in
every tenant namespace. In-cluster, values arrive via the pod spec
(downward API + Secrets); locally, via ``.env`` or the shell.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field

from synapse.constants import (
    DEFAULT_EVERMEMOS_URL,
    DEFAULT_GATEWAY_URL,
    DEFAULT_KEYCLOAK_ISSUER,
    DEFAULT_LANGFUSE_HOST,
    DEFAULT_LLM_BACKEND,
    DEFAULT_LLM_MODEL,
    DEFAULT_OTEL_ENDPOINT,
)

__all__ = [
    "DEFAULT_EVERMEMOS_URL",
    "DEFAULT_GATEWAY_URL",
    "DEFAULT_KEYCLOAK_ISSUER",
    "DEFAULT_LANGFUSE_HOST",
    "DEFAULT_OTEL_ENDPOINT",
    "SynapseConfig",
    "get_config",
]


class SynapseConfig(BaseModel):
    """Resolved configuration for one agent workload."""

    namespace: str = Field(
        default="default",
        description="Tenant namespace this workload runs as.",
    )
    agent_name: str = Field(default="synapse-agent")
    gateway_url: str = Field(
        default=DEFAULT_GATEWAY_URL,
        description="Base URL of the central AgentGateway proxy.",
    )
    gateway_token: str | None = Field(
        default=None,
        description=(
            "Keycloak-issued JWT for north-south calls through the ingress "
            "gateway. East-west (in-mesh) calls need no token. Real provider "
            "credentials are injected by the gateway — workloads never see "
            "API keys."
        ),
    )
    llm_backend: str = Field(
        default=DEFAULT_LLM_BACKEND,
        description="Name of the AgentgatewayBackend exposing the LLM provider.",
    )
    llm_model: str = Field(
        default=DEFAULT_LLM_MODEL,
        description="Model identifier sent in the request body.",
    )
    llm_base_url_override: str | None = Field(
        default=None,
        description=(
            "Direct OpenAI-compatible endpoint, bypassing the gateway — "
            "e.g. http://localhost:11434/v1 (local Ollama) or "
            "https://api.openai.com/v1 (standalone prod). When unset, LLM "
            "traffic flows through the platform gateway."
        ),
    )
    llm_api_key: str | None = Field(
        default=None,
        description=(
            "Real provider API key for direct mode (llm_base_url_override). "
            "Never set in platform mode — the gateway injects credentials."
        ),
    )
    evermemos_url: str = Field(
        default=DEFAULT_EVERMEMOS_URL,
        description="EverMemOS long-term memory REST endpoint.",
    )
    memory_user_id: str = Field(
        default="synapse-agent",
        description="User identity under which memories are stored.",
    )
    otel_endpoint: str = Field(
        default=DEFAULT_OTEL_ENDPOINT,
        description="OTLP gRPC collector endpoint (bridges to Langfuse).",
    )
    langfuse_host: str = Field(
        default=DEFAULT_LANGFUSE_HOST,
        description="Langfuse web UI / API base URL.",
    )
    keycloak_issuer: str = Field(default=DEFAULT_KEYCLOAK_ISSUER)
    keycloak_client_id: str | None = Field(default=None)
    keycloak_client_secret: str | None = Field(default=None)

    @property
    def llm_base_url(self) -> str:
        """OpenAI-compatible LLM endpoint for this workload.

        Direct mode (``llm_base_url_override`` set) wins; otherwise the
        tenant path on the platform gateway, which strips the
        ``/llm/{ns}/{backend}`` prefix, injects the real provider
        credential, applies prompt guards, and traces the call.
        """
        if self.llm_base_url_override:
            return self.llm_base_url_override
        return f"{self.gateway_url}/llm/{self.namespace}/{self.llm_backend}/v1"

    @property
    def keycloak_token_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/token"

    def mcp_url(self, server: str, namespace: str | None = None) -> str:
        """MCP endpoint for a tool server, defaulting to this tenant's namespace."""
        return f"{self.gateway_url}/mcp/{namespace or self.namespace}/{server}"

    def a2a_url(self, namespace: str, agent: str) -> str:
        """A2A endpoint of another agent on the platform."""
        return f"{self.gateway_url}/a2a/{namespace}/{agent}"


@lru_cache
def get_config() -> SynapseConfig:
    """Load config from the process environment (cached per process)."""
    env = os.environ
    return SynapseConfig(
        namespace=env.get("POD_NAMESPACE", env.get("SYNAPSE_NAMESPACE", "default")),
        agent_name=env.get("SYNAPSE_AGENT_NAME", "synapse-agent"),
        gateway_url=env.get("SYNAPSE_GATEWAY_URL", DEFAULT_GATEWAY_URL),
        gateway_token=env.get("SYNAPSE_GATEWAY_TOKEN"),
        llm_backend=env.get("SYNAPSE_LLM_BACKEND", DEFAULT_LLM_BACKEND),
        llm_model=env.get("SYNAPSE_MODEL", DEFAULT_LLM_MODEL),
        llm_base_url_override=env.get("SYNAPSE_LLM_BASE_URL"),
        llm_api_key=env.get("SYNAPSE_API_KEY"),
        evermemos_url=env.get("SYNAPSE_EVERMEMOS_URL", DEFAULT_EVERMEMOS_URL),
        memory_user_id=env.get("MEMORY_USER_ID", "synapse-agent"),
        otel_endpoint=env.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT", DEFAULT_OTEL_ENDPOINT
        ),
        langfuse_host=env.get("LANGFUSE_HOST", DEFAULT_LANGFUSE_HOST),
        keycloak_issuer=env.get("SYNAPSE_KEYCLOAK_ISSUER", DEFAULT_KEYCLOAK_ISSUER),
        keycloak_client_id=env.get("SYNAPSE_KEYCLOAK_CLIENT_ID"),
        keycloak_client_secret=env.get("SYNAPSE_KEYCLOAK_CLIENT_SECRET"),
    )
