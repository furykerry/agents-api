import pytest
from kubernetes.client import V1ObjectMeta, V1PodTemplateSpec, V1PodSpec, V1Container
from kubernetes.client.exceptions import ApiException

from agents import SandboxSetClient, SandboxClaimClient
from agents.models.sandboxset import SandboxSet, Spec as SandboxSetSpec
from agents.models.sandboxclaim import SandboxClaim, Spec as SandboxClaimSpec
from helpers import GROUP, VERSION, NAMESPACE


def test_sandboxclaim_crud(sandboxset_client, sandboxclaim_client, unique_name, cleanup):
    """Test SandboxClaim CRUD: create pool -> create claim -> verify spec -> delete"""
    print("=== Test SandboxClaim CRUD Operations ===")
    pool_name = f"{unique_name}-pool"
    claim_name = f"{unique_name}-claim"
    
    # Step 1: Create a SandboxSet pool with replicas=2
    print(f"  Step: Creating SandboxSet pool '{pool_name}' with replicas=2")
    sandboxset = SandboxSet(
        metadata=V1ObjectMeta(name=pool_name, namespace=NAMESPACE, labels={"app": "pool"}),
        spec=SandboxSetSpec(
            replicas=2,
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels={"app": "sandbox-pool"}),
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
    
    created_pool = sandboxset_client.create_sandboxset(sandboxset)
    assert created_pool["metadata"]["name"] == pool_name
    cleanup(GROUP, VERSION, NAMESPACE, "sandboxsets", pool_name)
    
    # Step 2: Create SandboxClaim
    print(f"  Step: Creating SandboxClaim '{claim_name}'")
    claim = SandboxClaim(
        metadata=V1ObjectMeta(name=claim_name, namespace=NAMESPACE),
        spec=SandboxClaimSpec(
            templateName=pool_name,
            replicas=1
        )
    )
    
    created_claim = sandboxclaim_client.create_sandboxclaim(claim)
    assert created_claim["metadata"]["name"] == claim_name
    cleanup(GROUP, VERSION, NAMESPACE, "sandboxclaims", claim_name)
    
    # Verify claim spec
    print(f"  Step: Verifying SandboxClaim '{claim_name}' spec")
    got_claim = sandboxclaim_client.get_sandboxclaim(claim_name)
    assert got_claim["spec"]["templateName"] == pool_name
    assert got_claim["spec"]["replicas"] == 1
    print(f"  Verified: templateName = {got_claim['spec']['templateName']}, replicas = {got_claim['spec']['replicas']}")
    
    # Step 3: Delete claim
    print(f"  Step: Deleting SandboxClaim '{claim_name}'")
    sandboxclaim_client.delete_sandboxclaim(claim_name)

    # Verify claim deletion
    print(f"  Step: Verifying deletion of '{claim_name}'")
    with pytest.raises(ApiException) as exc_info:
        sandboxclaim_client.get_sandboxclaim(claim_name)
    assert exc_info.value.status == 404

    # Step 4: Delete pool
    print(f"  Step: Deleting SandboxSet pool '{pool_name}'")
    sandboxset_client.delete_sandboxset(pool_name)
