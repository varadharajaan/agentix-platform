"""Tracing: every agent run lands in Langfuse with full GenAI semantics.

Two complementary paths exist on the platform:

1. **OTEL collector** (recommended in-cluster) — workloads emit OTLP gRPC
   to the namespace-local collector, which bridges spans into Langfuse
   with the platform's credentials. ``otel_environment`` returns the env
   vars a pod needs.
2. **Langfuse SDK callback** — a LangChain callback handler that ships
   traces directly; useful locally and for ad-hoc debugging. Requires the
   per-tenant ``langfuse-api-keys`` secret (created at onboarding).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from synapse.config import SynapseConfig, get_config

if TYPE_CHECKING:
    from langfuse.langchain import CallbackHandler


def otel_environment(config: SynapseConfig | None = None) -> dict[str, str]:
    """Env vars wiring OTEL SDKs to the platform collector.

    Merge into a Deployment's ``env`` (or export locally) so any
    OTEL-instrumented library traces without further code.
    """
    cfg = config or get_config()
    return {
        "OTEL_EXPORTER_OTLP_ENDPOINT": cfg.otel_endpoint,
        "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
        "OTEL_EXPORTER_OTLP_INSECURE": "true",
        "OTEL_SERVICE_NAME": cfg.agent_name,
        "OTEL_RESOURCE_ATTRIBUTES": (
            f"service.namespace={cfg.namespace},deployment.environment=platform"
        ),
    }


def get_langfuse_handler(
    config: SynapseConfig | None = None,
    *,
    trace_name: str | None = None,
    **kwargs: Any,
) -> CallbackHandler:
    """A LangChain callback handler streaming traces to Langfuse.

    Reads ``LANGFUSE_PUBLIC_KEY`` / ``LANGFUSE_SECRET_KEY`` from the
    environment (injected from the per-tenant ``langfuse-api-keys``
    secret). Pass the handler via any graph call::

        graph.ainvoke(state, config={"callbacks": [get_langfuse_handler()]})
    """
    try:
        from langfuse.langchain import CallbackHandler
    except ImportError as exc:
        raise ImportError(
            "langfuse is not installed — add the tracing extra: "
            "pip install 'synapse-agentic[tracing]'"
        ) from exc

    cfg = config or get_config()
    os.environ.setdefault("LANGFUSE_HOST", cfg.langfuse_host)
    return CallbackHandler(trace_name=trace_name or cfg.agent_name, **kwargs)
