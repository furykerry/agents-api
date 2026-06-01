import pytest
from kubernetes.client import V1ObjectMeta, V1PodTemplateSpec, V1PodSpec, V1Container
from kubernetes.client.exceptions import ApiException

from agents import SandboxClient
from agents.models.sandbox import Sandbox, Spec as SandboxSpec
from helpers import GROUP, VERSION, NAMESPACE


def test_sandbox_crud(sandbox_client, k8s_api, unique_name, cleanup):
    """Test Sandbox CRUD operations: create -> get -> patch labels -> list -> delete"""
    print("=== Test Sandbox CRUD Operations ===")
    name = f"{unique_name}-sandbox"
    
    # Create Sandbox
    print("  Step: Creating Sandbox")
    sandbox = Sandbox(
        metadata=V1ObjectMeta(name=name, namespace=NAMESPACE, labels={"app": "test"}),
        spec=SandboxSpec(
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels={"app": "sandbox-test"}),
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
    created = sandbox_client.create_sandbox(sandbox)
    assert created["metadata"]["name"] == name
    cleanup(GROUP, VERSION, NAMESPACE, "sandboxes", name)
    
    # Get sandbox
    print(f"  Step: Verifying sandbox '{name}' is created")
    got = sandbox_client.get_sandbox(name)
    assert got["metadata"]["name"] == name
    
    # Patch labels using dict (Sandbox model requires spec, so use raw dict for patch)
    print(f"  Step: Patching labels for '{name}'")
    patch_body = {
        "metadata": {
            "labels": {"app": "test", "patched": "true"}
        }
    }
    patched = sandbox_client.update_sandbox(name, patch_body)
    assert patched["metadata"]["labels"].get("patched") == "true"
    
    # List sandboxes
    print(f"  Step: Listing sandboxes by label")
    listed = k8s_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="sandboxes"
    )
    assert any(item["metadata"]["name"] == name for item in listed["items"])
    
    # Delete sandbox
    print(f"  Step: Deleting sandbox '{name}'")
    sandbox_client.delete_sandbox(name)
    
    # Verify deletion
    print(f"  Step: Verifying deletion of '{name}'")
    with pytest.raises(ApiException) as exc_info:
        sandbox_client.get_sandbox(name)
    assert exc_info.value.status == 404
