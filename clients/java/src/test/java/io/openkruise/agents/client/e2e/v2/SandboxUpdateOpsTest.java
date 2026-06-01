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
import io.openkruise.agents.client.v2.models.sandboxupdateopsspec.Selector;

import org.junit.Test;

import java.util.*;

import static org.junit.Assert.*;

/**
 * E2E tests for SandboxUpdateOps CRD.
 */
public class SandboxUpdateOpsTest extends BaseE2eTest {

    @Test
    public void testSandboxUpdateOpsBatchUpgrade() throws Exception {
        System.out.println("=== SandboxUpdateOps: batch upgrade ===");

        by("Creating a Sandbox for update ops targeting");
        String sandboxName = uniqueName("ops-target");
        Sandbox sandbox = new Sandbox();
        Map<String, String> sbxLabels = new HashMap<>();
        sbxLabels.put("e2e-ops-batch", "upgrade-test");
        sandbox.setMetadata(buildMeta(sandboxName, sbxLabels));

        SandboxSpec sbxSpec = new SandboxSpec();
        sbxSpec.setTemplate(basePodTemplate("ops-target"));
        sandbox.setSpec(sbxSpec);

        client.resources(Sandbox.class).inNamespace(NAMESPACE).resource(sandbox).create();
        cleanupActions.add(() -> client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(sandboxName).delete());

        by("Verifying sandbox is created");
        Sandbox gotSandbox = client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(sandboxName).get();
        assertNotNull(gotSandbox);

        by("Creating a SandboxUpdateOps to upgrade the sandbox");
        String opsName = uniqueName("test-ops");
        SandboxUpdateOps ops = new SandboxUpdateOps();
        ops.setMetadata(buildMeta(opsName));

        SandboxUpdateOpsSpec opsSpec = new SandboxUpdateOpsSpec();
        Selector selector = new Selector();
        Map<String, String> matchLabels = new HashMap<>();
        matchLabels.put("e2e-ops-batch", "upgrade-test");
        selector.setMatchLabels(matchLabels);
        opsSpec.setSelector(selector);

        String patchJson = "{\"spec\":{\"containers\":[{\"name\":\"test-container\",\"image\":\"nginx:stable-alpine3.23\"}]}}";
        io.fabric8.kubernetes.api.model.runtime.RawExtension patch =
                new io.fabric8.kubernetes.api.model.runtime.RawExtension(patchJson);
        opsSpec.setPatch(patch);
        ops.setSpec(opsSpec);

        SandboxUpdateOps created = client.resources(SandboxUpdateOps.class).inNamespace(NAMESPACE).resource(ops).create();
        assertNotNull(created);
        cleanupActions.add(() -> client.resources(SandboxUpdateOps.class).inNamespace(NAMESPACE).withName(opsName).delete());

        by("Verifying SandboxUpdateOps is created with correct selector");
        SandboxUpdateOps got = client.resources(SandboxUpdateOps.class).inNamespace(NAMESPACE).withName(opsName).get();
        assertNotNull(got);
        assertEquals("upgrade-test", got.getSpec().getSelector().getMatchLabels().get("e2e-ops-batch"));

        by("Listing SandboxUpdateOps");
        List<SandboxUpdateOps> list = client.resources(SandboxUpdateOps.class).inNamespace(NAMESPACE).list().getItems();
        assertTrue("Should have at least 1 SandboxUpdateOps", list.size() >= 1);

        by("Deleting the ops and waiting for it to be removed");
        client.resources(SandboxUpdateOps.class).inNamespace(NAMESPACE).withName(opsName).delete();
        eventuallyGone("sandboxupdateops deleted", TIMEOUT_SECONDS,
                () -> client.resources(SandboxUpdateOps.class).inNamespace(NAMESPACE).withName(opsName).get());
    }
}
