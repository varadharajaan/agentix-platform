# Deep Research — flagship Synapse example

A production-shaped agent that demonstrates every Synapse capability in one
workload:

| Concern | Mechanism |
| --- | --- |
| LLM access | `GatewayChatModel` → AgentGateway `/llm/{ns}/anthropic` — no API key in the pod |
| Tools | MCP search server via the gateway + long-term memory tools |
| Memory | `AtlasMemoryStore` (MongoDB Atlas Vector Search) when `SYNAPSE_MONGODB_URI` is set, else `EverMemStore` — findings persist across sessions |
| Tracing | LangSmith / Phoenix / Langfuse — env-selected, OTEL throughout |
| Protocol | A2A server (`AgentServer`) — invocable by any other platform agent |
| Deployment | `type: BYO` Agent CR; Kyverno auto-exposes `/a2a/{ns}/deep-research` |

## Run locally — Ollama (no cloud, no API keys)

The full plan → parallel-research → synthesize pipeline runs against a
local model. Verified end-to-end with `llama3.2:3b`:

```bash
# one-time: brew install ollama && ollama pull llama3.2:3b
ollama serve

pip install -e 'synapse[tracing,mcp]'
SYNAPSE_LLM_BASE_URL=http://localhost:11434/v1 \
SYNAPSE_MODEL=llama3.2:3b \
SYNAPSE_MEMORY_BACKEND=none \
python agent.py
```

Then:

```bash
curl -s localhost:8080/.well-known/agent.json | jq
curl -s localhost:8080 -H 'content-type: application/json' -d '{
  "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
  "params": {"message": {"role": "user",
    "parts": [{"type": "text", "text": "Compare vector DBs for agent memory"}]}}
}' | jq
```

## Run locally — against the platform gateway

```bash
pip install -e 'synapse[tracing,mcp,atlas]'
export SYNAPSE_GATEWAY_URL=http://localhost:15004   # port-forwarded gateway
python agent.py
```

## Deploy standalone — your own API key, any cluster

No Agentix platform required: `manifests.standalone.yaml` is a plain
Secret + Deployment + Service. Declare your key once in the Secret; the
pod calls the provider directly via `SYNAPSE_LLM_BASE_URL`:

```bash
$EDITOR manifests.standalone.yaml   # SYNAPSE_API_KEY: "sk-..." (+ model/endpoint)
kubectl apply -f manifests.standalone.yaml
```

Defaults to OpenAI (`gpt-4o-mini`); any OpenAI-compatible endpoint works.
Memory ships as `none` — uncomment the Atlas env block to enable it.

## Deploy to the platform

```bash
# Build & push (run from the repo root — the Dockerfile needs synapse/ in context)
docker build -f synapse/examples/deep_research/Dockerfile \
  -t <account>.dkr.ecr.us-east-1.amazonaws.com/agentix-platform/deep-research:v0.1.0 .
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/agentix-platform/deep-research:v0.1.0

# Point the manifest at your tenant namespace and image, then apply
kubectl apply -f manifests.yaml
```

The agent appears in the kagent UI and the AgentRegistry, and is callable
from any namespace:

```bash
curl -s http://localhost:15004/a2a/tenant-alpha/deep-research/.well-known/agent.json | jq
```
