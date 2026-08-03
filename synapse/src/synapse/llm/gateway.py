"""Chat models that route through the platform gateway.

``GatewayChatModel`` is a drop-in ``ChatOpenAI`` whose endpoint is the
AgentGateway LLM path for the caller's tenant namespace. Two platform
properties fall out for free:

- **Zero standing credentials** — the pod sends a placeholder key; the
  gateway strips it and injects the real provider credential from its own
  secret store. A compromised workload yields no API key.
- **Governance in the path** — prompt guards (PII rejection), rate limits,
  and GenAI tracing to Langfuse are enforced at the proxy, uniformly, for
  every agent on the platform.
"""

from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from synapse.config import SynapseConfig, get_config
from synapse.constants import PLACEHOLDER_API_KEY

__all__ = ["PLACEHOLDER_API_KEY", "GatewayChatModel"]


class GatewayChatModel(ChatOpenAI):
    """A chat model whose traffic flows through AgentGateway.

    Two modes, selected purely by environment:

    - **Gateway mode** (default) — traffic targets the tenant path on
      AgentGateway; the pod holds no credentials.
    - **Direct mode** (``SYNAPSE_LLM_BASE_URL`` set) — traffic targets any
      OpenAI-compatible endpoint directly: Ollama locally
      (``http://localhost:11434/v1``) or a provider in standalone prod
      (``https://api.openai.com/v1`` + ``SYNAPSE_API_KEY``).

    Args:
        config: Platform configuration; defaults to the process environment.
        model: Override the configured model identifier.
        **kwargs: Any other ``ChatOpenAI`` parameter (temperature, etc.).
    """

    def __init__(
        self,
        config: SynapseConfig | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        cfg = config or get_config()
        headers: dict[str, str] = {}
        if cfg.gateway_token and not cfg.llm_base_url_override:
            # North-south calls through the ingress gateway require a
            # Keycloak JWT; east-west mesh calls bypass authentication.
            headers["X-Platform-Token"] = cfg.gateway_token
        super().__init__(
            base_url=cfg.llm_base_url,
            api_key=cfg.llm_api_key or PLACEHOLDER_API_KEY,
            model=model or cfg.llm_model,
            default_headers=headers or None,
            **kwargs,
        )
