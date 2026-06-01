/*
Copyright 2025 The OpenKruise Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package io.openkruise.agents.client.e2e.v2;

import io.openkruise.agents.client.v2.models.*;

import org.junit.Test;

import static org.junit.Assert.*;

/**
 * E2E tests for SandboxClaim CRD.
 */
public class SandboxClaimTest extends BaseE2eTest {

    @Test
    public void testSandboxClaimBasicFlow() throws Exception {
        System.out.println("=== SandboxClaim: basic claim flow ===");

        by("Creating a SandboxSet pool with replicas=3");
        String poolName = uniqueName("test-pool");
        SandboxSet pool = new SandboxSet();
        pool.setMetadata(buildMeta(poolName));

        SandboxSetSpec poolSpec = new SandboxSetSpec();
        poolSpec.setReplicas(3);
        poolSpec.setTemplate(basePodTemplate("claim-pool"));
        pool.setSpec(poolSpec);

        client.resources(SandboxSet.class).inNamespace(NAMESPACE).resource(pool).create();
        cleanupActions.add(() -> client.resources(SandboxSet.class).inNamespace(NAMESPACE).withName(poolName).delete());

        by("Verifying SandboxSet pool is created");
        SandboxSet gotPool = client.resources(SandboxSet.class).inNamespace(NAMESPACE).withName(poolName).get();
        assertNotNull(gotPool);
        assertEquals(Integer.valueOf(3), gotPool.getSpec().getReplicas());

        by("Creating a SandboxClaim with replicas=1");
        String claimName = uniqueName("test-claim");
        SandboxClaim claim = new SandboxClaim();
        claim.setMetadata(buildMeta(claimName));

        SandboxClaimSpec claimSpec = new SandboxClaimSpec();
        claimSpec.setTemplateName(poolName);
        claimSpec.setReplicas(1);
        claim.setSpec(claimSpec);

        client.resources(SandboxClaim.class).inNamespace(NAMESPACE).resource(claim).create();
        cleanupActions.add(() -> client.resources(SandboxClaim.class).inNamespace(NAMESPACE).withName(claimName).delete());

        by("Verifying the SandboxClaim is created");
        SandboxClaim gotClaim = client.resources(SandboxClaim.class).inNamespace(NAMESPACE).withName(claimName).get();
        assertNotNull(gotClaim);
        assertEquals(poolName, gotClaim.getSpec().getTemplateName());
        assertEquals(Integer.valueOf(1), gotClaim.getSpec().getReplicas());

        by("Deleting the claim and waiting for it to be removed");
        client.resources(SandboxClaim.class).inNamespace(NAMESPACE).withName(claimName).delete();
        eventuallyGone("sandboxclaim deleted", TIMEOUT_SECONDS,
                () -> client.resources(SandboxClaim.class).inNamespace(NAMESPACE).withName(claimName).get());
    }
}
