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

import io.openkruise.agents.client.v2.models.Checkpoint;
import io.openkruise.agents.client.v2.models.CheckpointSpec;

import org.junit.Test;

import java.util.*;

import static org.junit.Assert.*;

/**
 * E2E tests for Checkpoint CRD.
 */
public class CheckpointTest extends BaseE2eTest {

    @Test
    public void testCheckpointCRUD() throws Exception {
        System.out.println("=== Checkpoint: CRUD operations ===");
        String name = uniqueName("test-checkpoint");

        by("Creating a new Checkpoint");
        Checkpoint checkpoint = new Checkpoint();
        Map<String, String> labels = new HashMap<>();
        labels.put("app", "e2e-test-java");
        checkpoint.setMetadata(buildMeta(name, labels));

        CheckpointSpec spec = new CheckpointSpec();
        spec.setSandboxName("test-sandbox");
        spec.setPodName("test-pod");
        spec.setKeepRunning(true);
        checkpoint.setSpec(spec);

        Checkpoint created = client.resources(Checkpoint.class).inNamespace(NAMESPACE).resource(checkpoint).create();
        assertNotNull(created);
        assertEquals("test-sandbox", created.getSpec().getSandboxName());
        cleanupActions.add(() -> client.resources(Checkpoint.class).inNamespace(NAMESPACE).withName(name).delete());

        by("Verifying the checkpoint is created with correct spec");
        Checkpoint got = client.resources(Checkpoint.class).inNamespace(NAMESPACE).withName(name).get();
        assertNotNull(got);
        assertEquals("test-sandbox", got.getSpec().getSandboxName());
        assertEquals("test-pod", got.getSpec().getPodName());
        assertTrue(got.getSpec().getKeepRunning());

        by("Listing checkpoints by label");
        List<Checkpoint> list = client.resources(Checkpoint.class).inNamespace(NAMESPACE)
                .withLabel("app", "e2e-test-java").list().getItems();
        assertTrue("Should have at least 1 Checkpoint", list.size() >= 1);

        by("Deleting the checkpoint and waiting for it to be removed");
        client.resources(Checkpoint.class).inNamespace(NAMESPACE).withName(name).delete();
        eventuallyGone("checkpoint deleted", TIMEOUT_SECONDS,
                () -> client.resources(Checkpoint.class).inNamespace(NAMESPACE).withName(name).get());
    }
}
