# Synapse — the intelligence layer

` synapse ` is the LangGraph-native orchestration layer of Agentix Platform.
You author agents as graphs; the platform runs them as first-class,
mesh-enrolled, gateway-governed workloads.

```python
from synapse import AgentCard, AgentServer, GatewayChatModel
from synapse.graphs import create_deep_research_agent
from synapse.memory import AtlasMemoryStore   # or EverMemStore — pluggable

memory = AtlasMemoryStore(
    connection_string="mongodb+srv://…",
    embeddings=voyage_embeddings,
    user_id="research-agent",
)

graph = create_deep_research_agent(
    model=GatewayChatModel(),          # LLM via AgentGateway — no API keys
    tools=memory.as_tools(),           # long-term memory the agent can search
    name="deep-research",
)

AgentServer(graph, AgentCard(name="deep-research", description="...")).run()
```

## Why this layer exists

The platform (EKS, Istio Ambient, AgentGateway, kagent, Keycloak, Langfuse,
EverMemOS) solves the hard *infrastructure* problems of running agents:
identity, isolation, credential injection, observability. Synapse solves the
*authoring* problem: composing models, tools, memory, and other agents into
reliable behavior — with LangGraph as the execution model and the platform
as the runtime.

| Module | What it gives you |
| --- | --- |
| `synapse.graphs` | Four production templates: ReAct, Plan-Execute, Supervisor, Deep Research |
| `synapse.llm` | `GatewayChatModel` — any LLM call via the gateway; zero standing credentials |
| `synapse.memory` | Pluggable long-term memory: `AtlasMemoryStore` (MongoDB Atlas Vector Search, hybrid RRF) or `EverMemStore` (platform paved road) |
| `synapse.tools` | `load_mcp_tools` — MCP tool servers through the gateway |
| `synapse.tracing` | LangSmith / Phoenix / Langfuse — pick by environment, not code |
| `synapse.runtime` | `AgentServer` (A2A protocol) and Agent-manifest export |
| `synapse.cli` | `synapse new` / `serve` / `export` |

## Install & test

```bash
pip install -e '.[dev,tracing,mcp]'
pytest
```

All tests run offline — HTTP dependencies are mocked, graphs run against
fake models.

## Deploy

```bash
synapse export my_agent:graph --image <ecr>/my-agent:v1 --namespace tenant-alpha
kubectl apply -f agent.yaml
```

See [examples/deep_research](examples/deep_research/) for the flagship
deployment.
