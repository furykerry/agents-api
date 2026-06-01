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

import io.openkruise.agents.client.v2.models.SandboxSet;
import io.openkruise.agents.client.v2.models.SandboxSetSpec;

import org.junit.Test;

import java.util.*;

import static org.junit.Assert.*;

/**
 * E2E tests for SandboxSet CRD.
 */
public class SandboxSetTest extends BaseE2eTest {

    @Test
    public void testSandboxSetCreationAndScaleUp() throws Exception {
        System.out.println("=== SandboxSet: creation and scale up ===");
        String name = uniqueName("test-sandboxset");

        by("Creating a new SandboxSet with replicas=2");
        SandboxSet sandboxSet = new SandboxSet();
        Map<String, String> labels = new HashMap<>();
        labels.put("sandboxset", "true");
        sandboxSet.setMetadata(buildMeta(name, labels));

        SandboxSetSpec spec = new SandboxSetSpec();
        spec.setReplicas(2);
        spec.setTemplate(basePodTemplate("sandboxset-e2e"));
        sandboxSet.setSpec(spec);

        client.resources(SandboxSet.class).inNamespace(NAMESPACE).resource(sandboxSet).create();
        cleanupActions.add(() -> client.resources(SandboxSet.class).inNamespace(NAMESPACE).withName(name).delete());

        by("Verifying the sandboxset is created");
        SandboxSet got = client.resources(SandboxSet.class).inNamespace(NAMESPACE).withName(name).get();
        assertNotNull(got);
        assertEquals(Integer.valueOf(2), got.getSpec().getReplicas());

        by("Scaling up sandboxset to 3");
        SandboxSet current = client.resources(SandboxSet.class).inNamespace(NAMESPACE).withName(name).get();
        current.getSpec().setReplicas(3);
        SandboxSet updated = client.resources(SandboxSet.class).inNamespace(NAMESPACE).resource(current).update();
        assertEquals(Integer.valueOf(3), updated.getSpec().getReplicas());

        by("Deleting the sandboxset and waiting for it to be removed");
        client.resources(SandboxSet.class).inNamespace(NAMESPACE).withName(name).delete();
        eventuallyGone("sandboxset deleted", TIMEOUT_SECONDS,
                () -> client.resources(SandboxSet.class).inNamespace(NAMESPACE).withName(name).get());
    }
}
