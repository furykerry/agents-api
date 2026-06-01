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

import io.fabric8.kubernetes.api.model.*;
import io.fabric8.kubernetes.client.KubernetesClient;
import io.fabric8.kubernetes.client.KubernetesClientBuilder;

import org.junit.After;
import org.junit.Before;

import java.util.*;
import java.util.function.Supplier;

import static org.junit.Assert.fail;

import java.util.logging.Logger;

/**
 * Base class for E2E tests providing common utilities.
 * Follows the Ginkgo BDD pattern used in openkruise/agents controller e2e tests.
 */
public abstract class BaseE2eTest {

    private static final Logger LOG = Logger.getLogger(BaseE2eTest.class.getName());

    protected static final String NAMESPACE = "default";
    protected static final String INITIAL_IMAGE = "nginx:stable-alpine3.20";
    protected static final long TIMEOUT_SECONDS = 90;
    protected static final long POLL_INTERVAL_MS = 500;

    protected KubernetesClient client;
    protected final List<Runnable> cleanupActions = new ArrayList<>();

    @Before
    public void setUp() {
        client = new KubernetesClientBuilder().build();
    }

    @After
    public void tearDown() {
        for (int i = cleanupActions.size() - 1; i >= 0; i--) {
            try {
                cleanupActions.get(i).run();
            } catch (Exception ignored) {}
        }
        cleanupActions.clear();
        if (client != null) {
            client.close();
        }
    }

    protected String uniqueName(String prefix) {
        return prefix + "-" + UUID.randomUUID().toString().substring(0, 8);
    }

    /**
     * Build ObjectMeta with name, namespace, and optional labels.
     */
    protected ObjectMeta buildMeta(String name, Map<String, String> labels) {
        ObjectMeta meta = new ObjectMeta();
        meta.setName(name);
        meta.setNamespace(NAMESPACE);
        if (labels != null) {
            meta.setLabels(labels);
        }
        return meta;
    }

    /**
     * Build ObjectMeta with name and namespace only.
     */
    protected ObjectMeta buildMeta(String name) {
        return buildMeta(name, null);
    }

    protected PodTemplateSpec basePodTemplate(String appLabel) {
        PodTemplateSpec template = new PodTemplateSpec();
        ObjectMeta meta = new ObjectMeta();
        Map<String, String> labels = new HashMap<>();
        labels.put("app", appLabel);
        meta.setLabels(labels);
        template.setMetadata(meta);

        PodSpec podSpec = new PodSpec();
        podSpec.setRestartPolicy("Never");
        Container container = new Container();
        container.setName("test-container");
        container.setImage(INITIAL_IMAGE);
        ContainerPort port = new ContainerPort();
        port.setName("http");
        port.setContainerPort(80);
        container.setPorts(Collections.singletonList(port));
        podSpec.setContainers(Collections.singletonList(container));
        template.setSpec(podSpec);

        return template;
    }

    /**
     * Poll until a resource is fully deleted (get returns null).
     * Tolerates transient exceptions during polling.
     */
    protected <T> void eventuallyGone(String description, long timeoutSec, Supplier<T> supplier)
            throws InterruptedException {
        long deadline = System.currentTimeMillis() + timeoutSec * 1000;
        Exception lastError = null;
        while (System.currentTimeMillis() < deadline) {
            try {
                T result = supplier.get();
                if (result == null) {
                    return;
                }
                lastError = null;
            } catch (Exception e) {
                // Resource not found exceptions mean deletion succeeded
                if (e.getMessage() != null && e.getMessage().contains("Not Found")) {
                    return;
                }
                lastError = e;
                LOG.fine("Transient error while polling deletion for '" + description + "': " + e.getMessage());
            }
            Thread.sleep(POLL_INTERVAL_MS);
        }
        String msg = "Timed out waiting for deletion: " + description;
        if (lastError != null) {
            msg += ", last error: " + lastError.getMessage();
        }
        fail(msg);
    }

    protected void by(String step) {
        System.out.println("  By: " + step);
    }
}
