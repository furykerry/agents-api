import pytest
from kubernetes.client import V1ObjectMeta
from kubernetes.client.exceptions import ApiException

from agents.models.checkpoint import Checkpoint, Spec as CheckpointSpec
from helpers import GROUP, VERSION, NAMESPACE


def test_checkpoint_crud(k8s_api, unique_name, cleanup):
    """Test Checkpoint CRUD operations: Create -> Get -> List -> Delete -> verify deletion"""
    print("=== Test Checkpoint CRUD Operations ===")
    name = f"{unique_name}-checkpoint"
    
    # Create Checkpoint
    print(f"  Step: Creating Checkpoint '{name}'")
    checkpoint = Checkpoint(
        apiVersion=f"{GROUP}/{VERSION}",
        kind="Checkpoint",
        metadata=V1ObjectMeta(name=name, namespace=NAMESPACE),
        spec=CheckpointSpec(
            sandboxName="test-sandbox",
            podName="test-pod"
        )
    )
    
    body = checkpoint.model_dump(exclude_unset=True, by_alias=True)
    created = k8s_api.create_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="checkpoints",
        body=body
    )
    assert created["metadata"]["name"] == name
    cleanup(GROUP, VERSION, NAMESPACE, "checkpoints", name)
    
    # Get Checkpoint
    print(f"  Step: Verifying Checkpoint '{name}' is created")
    def get_checkpoint():
        return k8s_api.get_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural="checkpoints",
            name=name
        )
    
    fetched = get_checkpoint()
    assert fetched["metadata"]["name"] == name
    
    # List Checkpoints
    print(f"  Step: Listing Checkpoints")
    listed = k8s_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="checkpoints"
    )
    assert any(item["metadata"]["name"] == name for item in listed["items"])
    
    # Delete Checkpoint
    print(f"  Step: Deleting Checkpoint '{name}'")
    k8s_api.delete_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="checkpoints",
        name=name
    )
    
    # Verify deletion
    print(f"  Step: Verifying deletion of '{name}'")
    with pytest.raises(ApiException) as exc_info:
        get_checkpoint()
    assert exc_info.value.status == 404
