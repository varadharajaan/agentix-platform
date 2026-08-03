"""Pluggable tracing: LangSmith, Arize Phoenix, or platform Langfuse."""

from synapse.tracing.langfuse import get_langfuse_handler, otel_environment
from synapse.tracing.setup import get_tracing_callbacks, phoenix_environment

__all__ = [
    "get_langfuse_handler",
    "get_tracing_callbacks",
    "otel_environment",
    "phoenix_environment",
]
