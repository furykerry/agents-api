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

import io.openkruise.agents.client.v2.models.Sandbox;
import io.openkruise.agents.client.v2.models.SandboxSpec;

import org.junit.Test;

import java.util.*;

import static org.junit.Assert.*;

/**
 * E2E tests for Sandbox CRD.
 */
public class SandboxTest extends BaseE2eTest {

    @Test
    public void testSandboxCreationAndRunningPhase() throws Exception {
        System.out.println("=== Sandbox: creation and running phase ===");
        String name = uniqueName("test-sandbox");

        by("Creating a new Sandbox");
        Sandbox sandbox = new Sandbox();
        sandbox.setMetadata(buildMeta(name));

        SandboxSpec spec = new SandboxSpec();
        spec.setTemplate(basePodTemplate("sandbox-e2e"));
        sandbox.setSpec(spec);

        Sandbox created = client.resources(Sandbox.class).inNamespace(NAMESPACE).resource(sandbox).create();
        assertNotNull(created);
        cleanupActions.add(() -> client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(name).delete());

        by("Verifying the sandbox is created");
        Sandbox got = client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(name).get();
        assertNotNull(got);
        assertEquals(name, got.getMetadata().getName());


    }

    @Test
    public void testSandboxUpdate() throws Exception {
        System.out.println("=== Sandbox: update labels ===");
        String name = uniqueName("test-sandbox-update");

        by("Creating a new Sandbox");
        Sandbox sandbox = new Sandbox();
        Map<String, String> labels = new HashMap<>();
        labels.put("app", "e2e-test-java");
        sandbox.setMetadata(buildMeta(name, labels));

        SandboxSpec spec = new SandboxSpec();
        spec.setTemplate(basePodTemplate("sandbox-update"));
        sandbox.setSpec(spec);

        client.resources(Sandbox.class).inNamespace(NAMESPACE).resource(sandbox).create();
        cleanupActions.add(() -> client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(name).delete());

        by("Updating sandbox labels");
        Sandbox got = client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(name).get();
        got.getMetadata().getLabels().put("updated", "true");
        Sandbox updated = client.resources(Sandbox.class).inNamespace(NAMESPACE).resource(got).update();
        assertEquals("true", updated.getMetadata().getLabels().get("updated"));

        by("Listing sandboxes by label");
        List<Sandbox> list = client.resources(Sandbox.class).inNamespace(NAMESPACE)
                .withLabel("app", "e2e-test-java").list().getItems();
        assertTrue("Should have at least 1 Sandbox", list.size() >= 1);

        by("Deleting the sandbox and waiting for it to be removed");
        client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(name).delete();
        eventuallyGone("sandbox deleted", TIMEOUT_SECONDS,
                () -> client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(name).get());
    }
}
