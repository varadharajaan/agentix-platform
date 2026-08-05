# Architecture deep-dive

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/architecture.svg"/>
  <img src="diagrams/architecture-light.svg" alt="Agentix Platform architecture" width="100%"/>
</picture>

Agentix Platform is a multi-tenant agentic AI platform on AWS EKS. It is
organized as six concentric layers, each with a single responsibility and a
explicit trust boundary.

## 1. Edge

| Component | Role |
| --- | --- |
| Route53 + ALB | Public ingress, TLS termination |
| Keycloak | OIDC identity provider; issues JWTs with tenant (`organization`) claims |
| OpenFGA | Fine-grained authorization (relationship-based) |

Every north-south request carries a Keycloak JWT. The ingress gateway
verifies it against the realm JWKS and enforces `jwtAuthentication: Strict`
plus the presence of an `organization` claim — there is no anonymous path
into the platform.

## 2. Traffic

Two gateways, one engine (AgentGateway, on Istio Ambient Mesh):

- **Ingress gateway** — `/a2a/{ns}/{agent}`, `/mcp/{ns}/{server}`,
  `/llm/{ns}/{backend}` routes; JWT verification; tenant-aware path routing.
- **Egress gateway** — the *only* path to external providers. Injects real
  API keys from its own secret store, applies prompt guards (PII rejection),
  rate limits, and emits GenAI traces. Workloads never hold provider
  credentials — a compromised pod yields nothing.

Kyverno watches for `Agent` resources annotated
`platform.agentic.io/expose: "true"` and auto-generates the corresponding
A2A `HTTPRoute` — exposing an agent is an annotation, not a pull request.

## 3. Orchestration (control plane)

- **kagent** reconciles `Agent`, `ModelConfig`, and `MCPServer` CRDs into
  Deployments, Services, and gateway configuration.
- **AgentRegistry** is the discovery surface: every exposed agent publishes
  an A2A agent card.
- **Synapse workloads** deploy as `type: BYO` Agents — bring your own
  container, get mesh enrollment and gateway exposure for free.

## 4. Synapse (the intelligence layer)

LangGraph graphs running as tenant workloads. See
[synapse.md](synapse.md) for the full guide. The key platform contracts:

- LLM calls target `http://agentgateway-proxy…/llm/{ns}/{backend}/v1` with a
  placeholder API key — the gateway swaps in the real credential.
- MCP tools load through `/mcp/{ns}/{server}` — same governance path.
- Memory defaults to **MongoDB Atlas Vector Search**; EverMemOS is the
  paved-road in-cluster alternative.
- Traces flow to **LangSmith**, **Phoenix**, or the platform **Langfuse**
  pipeline via OTEL.

## 5. Data & observability

| Store | Purpose |
| --- | --- |
| MongoDB Atlas | Agent long-term memory (documents + vectors + sessions in one collection) |
| EverMemOS (optional) | Paved-road in-cluster memory service |
| RDS / ElastiCache / S3 | Platform service state |
| ClickHouse | Langfuse analytics |
| Prometheus + Grafana | Mesh and workload metrics |

## 6. Cells

Tenant workloads run in dedicated EKS cell clusters, fronted by a transit
gateway. Cells are identical and disposable — the control plane is the only
stateful core.

## Request lifecycle

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/request-flow.svg"/>
  <img src="diagrams/request-flow-light.svg" alt="Request flow" width="100%"/>
</picture>

1. **Client** sends `tasks/send` (A2A, JSON-RPC) with a Keycloak JWT.
2. **Ingress gateway** verifies the JWT and routes `/a2a/{ns}/{agent}`.
3. **Tenant waypoint** (Istio Ambient L7) enforces namespace policy; HBONE
   mTLS to the pod.
4. **Synapse agent** runs its LangGraph loop — planning, tool calls,
   memory reads/writes.
5. **Egress gateway** receives the agent's credential-less LLM call,
   injects the real key, applies prompt guards, forwards.
6. **LLM provider** responds; the stream flows back over SSE.

Side channels: memory traffic to Atlas (or EverMemOS), tool calls to MCP
servers via the gateway, and OTEL spans from every hop into the tracing
backend.

## Trust boundaries

- **North-south**: JWT + OpenFGA at the edge.
- **East-west**: ambient mesh mTLS; tenant NetworkPolicies are
  deny-by-default (the deep-research example ships the one egress rule it
  needs).
- **Egress**: single gateway choke point; no workload holds external
  credentials.
