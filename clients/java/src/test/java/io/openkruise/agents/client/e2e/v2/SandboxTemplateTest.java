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

import java.util.*;

import static org.junit.Assert.*;

/**
 * E2E tests for SandboxTemplate CRD.
 */
public class SandboxTemplateTest extends BaseE2eTest {

    @Test
    public void testSandboxTemplateCreateAndUse() throws Exception {
        System.out.println("=== SandboxTemplate: create and verify ===");
        String templateName = uniqueName("test-template");

        by("Creating a new SandboxTemplate");
        SandboxTemplate tmpl = new SandboxTemplate();
        Map<String, String> labels = new HashMap<>();
        labels.put("app", "e2e-test-java");
        tmpl.setMetadata(buildMeta(templateName, labels));

        SandboxTemplateSpec spec = new SandboxTemplateSpec();
        spec.setTemplate(basePodTemplate("template-e2e"));
        tmpl.setSpec(spec);

        SandboxTemplate created = client.resources(SandboxTemplate.class).inNamespace(NAMESPACE).resource(tmpl).create();
        assertNotNull(created);
        cleanupActions.add(() -> client.resources(SandboxTemplate.class).inNamespace(NAMESPACE).withName(templateName).delete());

        by("Verifying the template is created with correct spec");
        SandboxTemplate got = client.resources(SandboxTemplate.class).inNamespace(NAMESPACE).withName(templateName).get();
        assertNotNull(got);
        assertNotNull(got.getSpec().getTemplate());
        assertEquals("test-container", got.getSpec().getTemplate().getSpec().getContainers().get(0).getName());

        by("Listing templates by label");
        List<SandboxTemplate> list = client.resources(SandboxTemplate.class).inNamespace(NAMESPACE)
                .withLabel("app", "e2e-test-java").list().getItems();
        assertTrue("Should have at least 1 SandboxTemplate", list.size() >= 1);

        by("Creating a Sandbox from templateRef");
        String sandboxName = uniqueName("test-sandbox-from-tmpl");
        Sandbox sandbox = new Sandbox();
        sandbox.setMetadata(buildMeta(sandboxName));

        SandboxSpec sbxSpec = new SandboxSpec();
        sbxSpec.setTemplate(basePodTemplate("from-template"));
        sandbox.setSpec(sbxSpec);

        client.resources(Sandbox.class).inNamespace(NAMESPACE).resource(sandbox).create();
        cleanupActions.add(() -> client.resources(Sandbox.class).inNamespace(NAMESPACE).withName(sandboxName).delete());

        by("Deleting the template and waiting for it to be removed");
        client.resources(SandboxTemplate.class).inNamespace(NAMESPACE).withName(templateName).delete();
        eventuallyGone("sandboxtemplate deleted", TIMEOUT_SECONDS,
                () -> client.resources(SandboxTemplate.class).inNamespace(NAMESPACE).withName(templateName).get());
    }
}
