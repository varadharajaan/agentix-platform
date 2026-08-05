# Synapse guide

Synapse is the LangGraph-native orchestration layer of Agentix Platform.
You author agents as graphs; the platform runs them as first-class,
mesh-enrolled, gateway-governed workloads.

```bash
pip install -e '.[dev,tracing,mcp,atlas]'
```

## Graph templates

All factories return a compiled `StateGraph` — serve it, export it, or
compose it into a larger graph.

### ReAct — `create_react_agent`

The foundational reason-act-observe loop. Thin wrapper over LangChain's
`create_agent` with Synapse defaults.

### Plan-Execute — `create_plan_execute_agent`

Planner → executor (ReAct sub-agent) → replanner. The replanner adapts the
plan after every step, so the agent recovers from dead ends instead of
committing to a stale plan. `max_cycles` bounds the loop.

### Supervisor — `create_supervisor_agent`

A routing model coordinates named worker graphs, delegating one sub-task at
a time until it can finish. Workers are any compiled graph — all Synapse
templates compose.

### Deep Research — `create_deep_research_agent`

The flagship pattern: planner decomposes a question, researchers fan out in
**parallel** via LangGraph's `Send` API (each a ReAct sub-agent with
tools), and a synthesizer merges the cited briefs into one report.

## LLM access — `GatewayChatModel`

```python
from synapse.llm import GatewayChatModel

model = GatewayChatModel(temperature=0.2)
```

A drop-in `ChatOpenAI` whose endpoint is the AgentGateway LLM path for the
caller's tenant namespace. The pod sends a placeholder key; the gateway
injects the real provider credential, applies prompt guards, and traces the
call. **Zero standing credentials in the workload.**

## Memory — pluggable backends

```python
from synapse.memory import AtlasMemoryStore, EverMemStore, MemoryStore
```

Any `MemoryStore` implements `remember` / `recall` / `profile` and gets
LangChain tool bindings (`save_memory`, `search_memory`) via `as_tools()`.

### MongoDB Atlas Vector Search (default)

```python
from langchain_voyageai import VoyageAIEmbeddings

store = AtlasMemoryStore(
    connection_string=os.environ["SYNAPSE_MONGODB_URI"],
    embeddings=VoyageAIEmbeddings(model="voyage-3-large"),
    user_id="agent",
)
await store.ensure_indexes(dimensions=1024)   # idempotent
```

One collection holds documents, vectors, and sessions. Recall modes:

| `method=` | Mechanism |
| --- | --- |
| `"vector"` | `$vectorSearch` (cosine) with `user_id` pre-filter |
| `"text"` | Atlas Search lexical `text` query |
| `"hybrid"` (default) | both, fused client-side with reciprocal rank fusion (k=60) |

### EverMemOS (platform paved road)

```python
store = EverMemStore(group_id="research")
```

REST client for the in-cluster EverMemOS service (hybrid BM25 + vector +
reranker). Use when running fully inside the platform without Atlas.

## Tools — `load_mcp_tools`

```python
from synapse.tools import load_mcp_tools

tools = await load_mcp_tools("tavily-search")            # own namespace
tools = await load_mcp_tools("agents", namespace="kagent-system")
```

MCP servers are consumed through the gateway (`/mcp/{ns}/{server}`) — same
credential injection, authorization, and tracing as LLM traffic.

## Tracing — three backends, one switch

| Backend | How |
| --- | --- |
| LangSmith | `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` — LangChain auto-traces |
| Phoenix | merge `phoenix_environment()` into the pod env + `openinference-instrumentation-langchain` in the image |
| Langfuse (platform default) | `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` present → `get_tracing_callbacks()` returns the handler |

```python
from synapse.tracing import get_tracing_callbacks

await graph.ainvoke(state, config={"callbacks": get_tracing_callbacks()})
```

## Serving — `AgentServer`

```python
from synapse import AgentCard, AgentServer, Skill

AgentServer(
    graph,
    AgentCard(
        name="deep-research",
        description="...",
        skills=[Skill(id="research", name="Research", description="...")],
    ),
).run(port=8080)
```

Exposes the A2A protocol: `/.well-known/agent.json` discovery, JSON-RPC
`tasks/send`, and `tasks/sendSubscribe` with SSE streaming of graph tokens.

## Deploying — `synapse export`

```bash
synapse export my_agent:graph --image <ecr>/my-agent:v1 --namespace tenant-alpha
```

Emits a `kagent.dev/v1alpha2` `Agent` manifest (`type: BYO`) with:

- `POD_NAMESPACE` wired via the downward API (config resolves in-cluster),
- the `platform.agentic.io/expose` annotation → Kyverno auto-creates the
  `/a2a/{ns}/{name}` gateway route,
- sane resource requests/limits (override with `--env` / manifest edits).

## Configuration

Everything is environment-driven (`synapse.config.SynapseConfig`); the same
artifact runs unmodified in every tenant namespace.

| Variable | Default | Purpose |
| --- | --- | --- |
| `POD_NAMESPACE` | `default` | Tenant namespace (downward API in-cluster) |
| `SYNAPSE_GATEWAY_URL` | in-cluster AgentGateway service | Gateway base URL |
| `SYNAPSE_LLM_BACKEND` / `SYNAPSE_MODEL` | `anthropic` / `claude-sonnet-4-5` | Gateway backend + model id |
| `SYNAPSE_LLM_BASE_URL` | — | **Direct mode**: any OpenAI-compatible endpoint, bypassing the gateway — `http://localhost:11434/v1` (local Ollama), `https://api.openai.com/v1` (standalone prod) |
| `SYNAPSE_API_KEY` | — | Real provider key for direct mode only; never set in gateway mode |
| `SYNAPSE_MEMORY_BACKEND` | auto | `atlas` / `evermem` / `none` — example-level memory selection |
| `SYNAPSE_MONGODB_URI` | — | Atlas connection string (enables Atlas memory) |
| `SYNAPSE_EVERMEMOS_URL` | in-cluster EverMemOS | Paved-road memory endpoint |
| `SYNAPSE_KEYCLOAK_CLIENT_ID/SECRET` | — | North-south token acquisition |
| `LANGSMITH_TRACING` / `LANGFUSE_PUBLIC_KEY` … | — | Tracing backend selection |

Every default above (and all other literals — ports, index names, CRD
versions, resource presets, API paths) lives in exactly one place:
[`synapse/constants.py`](../synapse/src/synapse/constants.py). A guard
test (`tests/test_constants.py`) AST-scans the package and fails the build
if an operative literal appears anywhere else.

## Testing

```bash
pytest        # 31 tests, fully offline
ruff check src tests
```

Graphs run against `FakeListChatModel`; HTTP is mocked with `respx`; the
A2A server is exercised through an in-memory ASGI transport; the Atlas
store is tested against a fake collection (pipeline shapes + RRF logic).
