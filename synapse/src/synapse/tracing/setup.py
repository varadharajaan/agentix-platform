"""Tracing backend selection.

Synapse treats observability as a deployment choice, not a code change:

- **LangSmith** — LangGraph-native managed tracing. Set
  ``LANGSMITH_TRACING=true`` + ``LANGSMITH_API_KEY``; LangChain traces
  automatically, no handler needed.
- **Arize Phoenix** — OSS, OTEL-native, self-hostable on the platform.
  ``phoenix_environment()`` emits the env a pod needs; OpenInference
  auto-instruments LangChain.
- **Langfuse** (platform default) — the paved-road collector pipeline.
  ``get_tracing_callbacks()`` returns a LangChain callback handler when
  the per-tenant ``langfuse-api-keys`` are present.
"""

from __future__ import annotations

import os
from typing import Any

from synapse.config import SynapseConfig, get_config
from synapse.constants import DEFAULT_PHOENIX_ENDPOINT


def get_tracing_callbacks(config: SynapseConfig | None = None) -> list[Any]:
    """Callback handlers to pass to graph invocations.

    LangSmith needs no handler (env-driven auto-tracing); Phoenix uses
    OTEL auto-instrumentation. Returns a Langfuse handler when its keys
    are configured, otherwise an empty list.
    """
    if os.environ.get("LANGSMITH_TRACING", "").lower() == "true":
        return []  # LangChain auto-traces to LangSmith
    if os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"):
        return []  # OpenInference auto-instruments to Phoenix
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        from synapse.tracing.langfuse import get_langfuse_handler

        return [get_langfuse_handler(config)]
    return []


def phoenix_environment(
    endpoint: str = DEFAULT_PHOENIX_ENDPOINT,
    *,
    service_name: str | None = None,
) -> dict[str, str]:
    """Env vars wiring OpenInference traces to a platform-hosted Phoenix.

    Merge into a Deployment's ``env``; pair with
    ``openinference-instrumentation-langchain`` in the image.
    """
    cfg = get_config()
    return {
        "PHOENIX_COLLECTOR_ENDPOINT": endpoint,
        "OTEL_SERVICE_NAME": service_name or cfg.agent_name,
        "OTEL_RESOURCE_ATTRIBUTES": f"service.namespace={cfg.namespace}",
    }
