import pytest
from kubernetes.client import V1ObjectMeta, V1PodTemplateSpec, V1PodSpec, V1Container
from kubernetes.client.exceptions import ApiException

from agents.models.sandboxtemplate import SandboxTemplate, Spec as SandboxTemplateSpec
from helpers import GROUP, VERSION, NAMESPACE


def test_sandboxtemplate_crud(k8s_api, unique_name, cleanup):
    """Test SandboxTemplate CRUD operations: Create -> Get -> List -> Delete -> verify deletion"""
    print("=== Test SandboxTemplate CRUD Operations ===")
    name = f"{unique_name}-template"
    
    # Create SandboxTemplate
    print(f"  Step: Creating SandboxTemplate '{name}'")
    template = SandboxTemplate(
        apiVersion=f"{GROUP}/{VERSION}",
        kind="SandboxTemplate",
        metadata=V1ObjectMeta(name=name, namespace=NAMESPACE),
        spec=SandboxTemplateSpec(
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels={"app": "template-test"}),
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
    
    body = template.model_dump(exclude_unset=True, by_alias=True)
    created = k8s_api.create_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="sandboxtemplates",
        body=body
    )
    assert created["metadata"]["name"] == name
    cleanup(GROUP, VERSION, NAMESPACE, "sandboxtemplates", name)
    
    # Get SandboxTemplate
    print(f"  Step: Verifying SandboxTemplate '{name}' is created")
    def get_template():
        return k8s_api.get_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural="sandboxtemplates",
            name=name
        )
    
    fetched = get_template()
    assert fetched["metadata"]["name"] == name
    
    # List SandboxTemplates
    print(f"  Step: Listing SandboxTemplates")
    listed = k8s_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="sandboxtemplates"
    )
    assert any(item["metadata"]["name"] == name for item in listed["items"])
    
    # Delete SandboxTemplate
    print(f"  Step: Deleting SandboxTemplate '{name}'")
    k8s_api.delete_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="sandboxtemplates",
        name=name
    )
    
    # Verify deletion
    print(f"  Step: Verifying deletion of '{name}'")
    with pytest.raises(ApiException) as exc_info:
        get_template()
    assert exc_info.value.status == 404
