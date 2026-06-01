import pytest
from kubernetes.client import V1ObjectMeta, V1PodTemplateSpec, V1PodSpec, V1Container
from kubernetes.client.exceptions import ApiException

from agents import SandboxSetClient
from agents.models.sandboxset import SandboxSet, Spec as SandboxSetSpec
from helpers import GROUP, VERSION, NAMESPACE


def test_sandboxset_crud(sandboxset_client, unique_name, cleanup):
    """Test SandboxSet CRUD operations: create(replicas=2) -> get -> patch scale to 3 -> delete"""
    print("=== Test SandboxSet CRUD Operations ===")
    name = f"{unique_name}-sandboxset"
    
    # Create SandboxSet with replicas=2
    print("  Step: Creating SandboxSet with replicas=2")
    sandboxset = SandboxSet(
        metadata=V1ObjectMeta(name=name, namespace=NAMESPACE, labels={"app": "test"}),
        spec=SandboxSetSpec(
            replicas=2,
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels={"app": "sandboxset-test"}),
                spec=V1PodSpec(
                    restart_policy="Never",
                    containers=[V1Container(
                        name="main",
                        image="busybox:latest",
                        command=["sh", "-c", "sleep 3600"]
                    )]
                )
            )
        )
    )
    
    created = sandboxset_client.create_sandboxset(sandboxset)
    assert created["metadata"]["name"] == name
    assert created["spec"]["replicas"] == 2
    cleanup(GROUP, VERSION, NAMESPACE, "sandboxsets", name)
    
    # Get sandboxset
    print(f"  Step: Verifying SandboxSet '{name}' is created")
    got = sandboxset_client.get_sandboxset(name)
    assert got["metadata"]["name"] == name
    
    # Patch to scale to 3
    print(f"  Step: Scaling SandboxSet '{name}' to 3 replicas")
    patch_body = {
        "spec": {
            "replicas": 3
        }
    }
    patched = sandboxset_client.update_sandboxset(name, patch_body)
    assert patched["spec"]["replicas"] == 3
    print(f"  Verified: replicas = {patched['spec']['replicas']}")
    
    # Delete sandboxset
    print(f"  Step: Deleting SandboxSet '{name}'")
    sandboxset_client.delete_sandboxset(name)
    
    # Verify deletion
    print(f"  Step: Verifying deletion of '{name}'")
    with pytest.raises(ApiException) as exc_info:
        sandboxset_client.get_sandboxset(name)
    assert exc_info.value.status == 404
