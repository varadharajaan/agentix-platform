import yaml

from synapse.runtime.crd import build_agent_manifest
from synapse.runtime.server import Skill


def test_manifest_is_byo_agent_with_expose_annotation():
    doc = yaml.safe_load(
        build_agent_manifest(
            name="deep-research",
            namespace="tenant-alpha",
            image="registry/deep-research:v1",
            description="test agent",
            skills=[Skill(id="research", name="Research", description="does research")],
        )
    )

    assert doc["apiVersion"] == "kagent.dev/v1alpha2"
    assert doc["kind"] == "Agent"
    assert doc["metadata"]["name"] == "deep-research"
    assert doc["metadata"]["namespace"] == "tenant-alpha"
    assert doc["metadata"]["annotations"]["platform.agentic.io/expose"] == "true"

    spec = doc["spec"]
    assert spec["type"] == "BYO"
    assert spec["byo"]["deployment"]["image"] == "registry/deep-research:v1"
    assert spec["a2aConfig"]["skills"][0]["id"] == "research"


def test_manifest_without_expose_has_no_annotations():
    doc = yaml.safe_load(
        build_agent_manifest(
            name="internal",
            namespace="ns",
            image="img",
            description="d",
            expose=False,
        )
    )
    assert "annotations" not in doc["metadata"]


def test_manifest_carries_namespace_downward_api_env():
    doc = yaml.safe_load(
        build_agent_manifest(name="a", namespace="ns", image="img", description="d")
    )
    env = doc["spec"]["byo"]["deployment"]["env"]
    pod_ns = next(e for e in env if e["name"] == "POD_NAMESPACE")
    assert pod_ns["valueFrom"]["fieldRef"]["fieldPath"] == "metadata.namespace"


def test_manifest_expose_alias():
    doc = yaml.safe_load(
        build_agent_manifest(
            name="a",
            namespace="ns",
            image="img",
            description="d",
            expose_alias="shared",
        )
    )
    assert (
        doc["metadata"]["annotations"]["platform.agentic.io/expose-alias"] == "shared"
    )
