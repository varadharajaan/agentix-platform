"""Every default, endpoint, and protocol literal in Synapse — one module.

Nothing else in ``src/`` hardcodes a URL, port, model name, API path, or
resource preset; it imports from here. Environment variables (resolved in
``config.py``) override these at runtime — this module is the fallback
layer and the single place to audit what a workload will do.
"""

# --- A2A protocol ------------------------------------------------------------
A2A_PROTOCOL_VERSION = "0.3.0"

# --- Server ------------------------------------------------------------------
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080

# --- Platform service endpoints (in-cluster DNS) ------------------------------
DEFAULT_GATEWAY_URL = "http://agentgateway-proxy.agentgateway-system.svc.cluster.local"
DEFAULT_EVERMEMOS_URL = "http://evermemos.evermemos.svc.cluster.local:1995"
DEFAULT_OTEL_ENDPOINT = "http://otel-collector.langfuse.svc.cluster.local:4317"
DEFAULT_LANGFUSE_HOST = "http://langfuse-web.langfuse.svc.cluster.local:3000"
DEFAULT_KEYCLOAK_ISSUER = (
    "http://keycloak.keycloak.svc.cluster.local:8080/realms/agents"
)
DEFAULT_PHOENIX_ENDPOINT = "http://phoenix.observability.svc.cluster.local:6006"

# --- LLM ---------------------------------------------------------------------
DEFAULT_LLM_BACKEND = "anthropic"
DEFAULT_LLM_MODEL = "claude-sonnet-4-5"
#: Placeholder credential for gateway mode — the gateway overwrites the
#: Authorization header with the real provider key, so this value only has
#: to pass client-side validation. Intentionally not a secret.
PLACEHOLDER_API_KEY = "gateway-injected"
#: Well-known direct-mode endpoints (SYNAPSE_LLM_BASE_URL values).
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"

# --- EverMemOS REST API -------------------------------------------------------
EVERMEM_API_MEMORIES = "/api/v1/memories"
EVERMEM_API_SEARCH = "/api/v1/memories/search"
EVERMEM_API_CONVERSATION_META = "/api/v1/memories/conversation-meta"
EVERMEM_HEALTH_PATH = "/health"
EVERMEM_TIMEOUT_S = 30.0
DEFAULT_MEMORY_TYPES = ["profile", "episodic_memory", "foresight", "event_log"]

# --- MongoDB Atlas memory backend ---------------------------------------------
ATLAS_VECTOR_INDEX = "memory_vector_index"
ATLAS_TEXT_INDEX = "memory_text_index"
ATLAS_DEFAULT_DATABASE = "synapse"
ATLAS_DEFAULT_COLLECTION = "memories"
ATLAS_DEFAULT_DIMENSIONS = 1024
ATLAS_RRF_K = 60
DEFAULT_EMBEDDINGS_MODEL = "voyage-3-large"

# --- kagent Agent CRD export ---------------------------------------------------
KAGENT_API_VERSION = "kagent.dev/v1alpha2"
EXPOSE_ANNOTATION = "platform.agentic.io/expose"
EXPOSE_ALIAS_ANNOTATION = "platform.agentic.io/expose-alias"
DEFAULT_RESOURCES = {
    "requests": {"cpu": "100m", "memory": "256Mi"},
    "limits": {"cpu": "500m", "memory": "512Mi"},
}
