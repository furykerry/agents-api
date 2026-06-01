import pytest
from kubernetes.client import V1ObjectMeta, V1PodTemplateSpec, V1PodSpec, V1Container
from kubernetes.client.exceptions import ApiException

from agents import SandboxClient
from agents.models.sandbox import Sandbox, Spec as SandboxSpec
from agents.models.sandboxupdateops import SandboxUpdateOps, Spec as SandboxUpdateOpsSpec, Selector
from helpers import GROUP, VERSION, NAMESPACE


def test_sandboxupdateops_crud(sandbox_client, k8s_api, unique_name, cleanup):
    """Test SandboxUpdateOps CRUD: create Sandbox -> create UpdateOps -> verify selector -> List -> Delete"""
    print("=== Test SandboxUpdateOps CRUD Operations ===")
    sandbox_name = f"{unique_name}-sandbox"
    updateops_name = f"{unique_name}-updateops"
    
    # Step 1: Create a Sandbox
    print(f"  Step: Creating Sandbox '{sandbox_name}'")
    sandbox = Sandbox(
        metadata=V1ObjectMeta(name=sandbox_name, namespace=NAMESPACE, labels={"app": "update-test"}),
        spec=SandboxSpec(
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels={"app": "update-test"}),
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
    
    created_sandbox = sandbox_client.create_sandbox(sandbox)
    assert created_sandbox["metadata"]["name"] == sandbox_name
    cleanup(GROUP, VERSION, NAMESPACE, "sandboxes", sandbox_name)
    
    # Verify Sandbox is created
    print(f"  Step: Verifying Sandbox '{sandbox_name}' is created")
    got_sandbox = sandbox_client.get_sandbox(sandbox_name)
    assert got_sandbox["metadata"]["name"] == sandbox_name
    
    # Step 2: Create SandboxUpdateOps
    print(f"  Step: Creating SandboxUpdateOps '{updateops_name}'")
    update_ops = SandboxUpdateOps(
        apiVersion=f"{GROUP}/{VERSION}",
        kind="SandboxUpdateOps",
        metadata=V1ObjectMeta(name=updateops_name, namespace=NAMESPACE),
        spec=SandboxUpdateOpsSpec(
            selector=Selector(
                matchLabels={"app": "update-test"}
            ),
            patch={
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "main",
                                    "image": "busybox:1.36"
                                }
                            ]
                        }
                    }
                }
            }
        )
    )
    
    body = update_ops.model_dump(exclude_unset=True, by_alias=True)
    created_updateops = k8s_api.create_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="sandboxupdateops",
        body=body
    )
    assert created_updateops["metadata"]["name"] == updateops_name
    cleanup(GROUP, VERSION, NAMESPACE, "sandboxupdateops", updateops_name)
    
    # Verify selector
    print(f"  Step: Verifying SandboxUpdateOps selector")
    assert created_updateops["spec"]["selector"]["matchLabels"]["app"] == "update-test"
    print(f"  Verified: selector matchLabels app = {created_updateops['spec']['selector']['matchLabels']['app']}")
    
    # List UpdateOps
    print(f"  Step: Listing SandboxUpdateOps")
    listed = k8s_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="sandboxupdateops"
    )
    assert any(item["metadata"]["name"] == updateops_name for item in listed["items"])
    
    # Delete UpdateOps
    print(f"  Step: Deleting SandboxUpdateOps '{updateops_name}'")
    k8s_api.delete_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="sandboxupdateops",
        name=updateops_name
    )

    # Verify UpdateOps deletion
    print(f"  Step: Verifying deletion of '{updateops_name}'")
    with pytest.raises(ApiException) as exc_info:
        k8s_api.get_namespaced_custom_object(
            group=GROUP, version=VERSION, namespace=NAMESPACE,
            plural="sandboxupdateops", name=updateops_name
        )
    assert exc_info.value.status == 404
    
    # Delete Sandbox
    print(f"  Step: Deleting Sandbox '{sandbox_name}'")
    sandbox_client.delete_sandbox(sandbox_name)
