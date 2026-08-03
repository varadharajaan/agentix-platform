"""Load MCP tools through the platform gateway.

Tool servers on the platform are exposed as MCP endpoints behind
AgentGateway at ``/mcp/{namespace}/{server}`` — with the same credential
injection, authorization policy, and tracing as LLM traffic. Synapse
agents therefore consume tools without holding server credentials or
knowing where servers physically run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from synapse.config import SynapseConfig, get_config

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


async def load_mcp_tools(
    server: str,
    *,
    config: SynapseConfig | None = None,
    namespace: str | None = None,
) -> list[BaseTool]:
    """Load all tools from an MCP server via the gateway.

    Args:
        server: Name of the MCP server (its ``AgentgatewayBackend`` name).
        config: Platform configuration; defaults to the process environment.
        namespace: Override the tenant namespace segment (e.g. to reach a
            shared server in ``kagent-system``).

    Returns:
        LangChain tools ready to hand to any Synapse graph.
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as exc:
        raise ImportError(
            "MCP support is not installed — add the extra: "
            "pip install 'synapse-agentic[mcp]'"
        ) from exc

    cfg = config or get_config()
    headers = {}
    if cfg.gateway_token:
        headers["X-Platform-Token"] = cfg.gateway_token

    client = MultiServerMCPClient(
        {
            server: {
                "url": cfg.mcp_url(server, namespace),
                "transport": "streamable_http",
                "headers": headers,
            }
        }
    )
    return await client.get_tools()
