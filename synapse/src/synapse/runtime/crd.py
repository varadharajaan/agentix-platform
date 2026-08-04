"""Export a Synapse agent as a platform-native Agent manifest.

The platform reconciles ``kagent.dev/v1alpha2`` Agent resources of
``type: BYO`` into Deployments + Services, enrolls them into the ambient
mesh, and — when annotated ``platform.agentic.io/expose: "true"`` —
auto-generates the A2A HTTPRoute through the gateway. ``build_agent_manifest``
emits exactly that YAML for a containerized Synapse graph.
"""

from __future__ import annotations

from typing import Any

import yaml

from synapse.constants import (
    DEFAULT_PORT,
    DEFAULT_RESOURCES,
    EXPOSE_ALIAS_ANNOTATION,
    EXPOSE_ANNOTATION,
    KAGENT_API_VERSION,
)
from synapse.runtime.server import Skill


def build_agent_manifest(
    name: str,
    namespace: str,
    image: str,
    *,
    description: str,
    skills: list[Skill] | None = None,
    replicas: int = 1,
    port: int = DEFAULT_PORT,
    expose: bool = True,
    expose_alias: str | None = None,
    env: dict[str, str] | None = None,
    resources: dict[str, Any] | None = None,
) -> str:
    """Render a BYO Agent custom resource as YAML.

    Args:
        name: Agent name — becomes the Service name and A2A path segment.
        namespace: Tenant namespace to deploy into.
        image: Container image serving the ``AgentServer`` app.
        description: Human-readable purpose (shown in the agent registry).
        skills: A2A skills advertised on the agent card.
        replicas: Pod replicas.
        port: Container port the A2A server listens on.
        expose: When true, adds the annotation that makes Kyverno generate
            the ``/a2a/{namespace}/{name}`` gateway route.
        expose_alias: Optional alias replacing the namespace path segment.
        env: Extra environment variables for the container.
        resources: Kubernetes resource requests/limits.

    Returns:
        YAML document string ready for ``kubectl apply``.
    """
    annotations: dict[str, str] = {}
    if expose:
        annotations[EXPOSE_ANNOTATION] = "true"
    if expose_alias:
        annotations[EXPOSE_ALIAS_ANNOTATION] = expose_alias

    container_env = [
        {
            "name": "POD_NAMESPACE",
            "valueFrom": {"fieldRef": {"fieldPath": "metadata.namespace"}},
        },
        {"name": "SYNAPSE_AGENT_NAME", "value": name},
        {"name": "PORT", "value": str(port)},
    ]
    for key, value in (env or {}).items():
        container_env.append({"name": key, "value": value})

    manifest = {
        "apiVersion": KAGENT_API_VERSION,
        "kind": "Agent",
        "metadata": {
            "name": name,
            "namespace": namespace,
            **({"annotations": annotations} if annotations else {}),
        },
        "spec": {
            "description": description,
            "type": "BYO",
            "byo": {
                "deployment": {
                    "image": image,
                    "replicas": replicas,
                    "env": container_env,
                    "resources": resources or DEFAULT_RESOURCES,
                }
            },
            "a2aConfig": {
                "skills": [s.model_dump(exclude_none=True) for s in (skills or [])]
            },
        },
    }
    return yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False)
