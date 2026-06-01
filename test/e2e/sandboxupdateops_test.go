package e2e

import (
	"encoding/json"
	"fmt"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	agentsv1alpha1 "github.com/openkruise/agents-api/agents/v1alpha1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

var _ = Describe("SandboxUpdateOps", func() {
	var (
		sandbox *agentsv1alpha1.Sandbox
		ops     *agentsv1alpha1.SandboxUpdateOps
	)

	Context("batch upgrade", func() {
		var testLabels map[string]string

		BeforeEach(func() {
			testLabels = map[string]string{
				"app":        "sandbox-test",
				"managed-by": "ginkgo",
			}

			sandbox = &agentsv1alpha1.Sandbox{
				ObjectMeta: metav1.ObjectMeta{
					Name:      fmt.Sprintf("test-sandbox-%d", time.Now().UnixNano()),
					Namespace: Namespace,
					Labels:    testLabels,
				},
				Spec: agentsv1alpha1.SandboxSpec{
					EmbeddedSandboxTemplate: agentsv1alpha1.EmbeddedSandboxTemplate{
						Template: basePodTemplateSpec(map[string]string{"app": "sandbox-test"}),
					},
				},
			}
		})

		AfterEach(func() {
			By("Cleaning up SandboxUpdateOps and Sandbox")
			if ops != nil {
				_ = k8sClient.Delete(ctx, ops)
			}
			if sandbox != nil {
				_ = k8sClient.Delete(ctx, sandbox)
			}
		})

		It("should create Sandbox, apply update ops, and verify completion", func() {
			By("Creating Sandbox")
			Expect(k8sClient.Create(ctx, sandbox)).To(Succeed())

			By("Verifying Sandbox is created")
			Eventually(func() error {
				return k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandbox.Name,
					Namespace: sandbox.Namespace,
				}, sandbox)
			}, time.Second*5, time.Millisecond*500).Should(Succeed())

			By("Creating patch data to update image")
			patchData := map[string]interface{}{
				"spec": map[string]interface{}{
					"template": map[string]interface{}{
						"spec": map[string]interface{}{
							"containers": []map[string]interface{}{
								{
									"name":  "main",
									"image": "busybox:1.36",
								},
							},
						},
					},
				},
			}
			patchJSON, err := json.Marshal(patchData)
			Expect(err).NotTo(HaveOccurred())

			By("Creating SandboxUpdateOps")
			ops = &agentsv1alpha1.SandboxUpdateOps{
				ObjectMeta: metav1.ObjectMeta{
					Name:      fmt.Sprintf("test-sandboxupdateops-%d", time.Now().UnixNano()),
					Namespace: Namespace,
					Labels: map[string]string{
						"app":        "e2e-test",
						"managed-by": "ginkgo",
					},
				},
				Spec: agentsv1alpha1.SandboxUpdateOpsSpec{
					Selector: &metav1.LabelSelector{
						MatchLabels: testLabels,
					},
					Patch: runtime.RawExtension{
						Raw: patchJSON,
					},
				},
			}
			Expect(k8sClient.Create(ctx, ops)).To(Succeed())

			By("Verifying ops created with correct selector")
			got := &agentsv1alpha1.SandboxUpdateOps{}
			Expect(k8sClient.Get(ctx, types.NamespacedName{
				Name:      ops.Name,
				Namespace: ops.Namespace,
			}, got)).To(Succeed())
			Expect(got.Spec.Selector).ToNot(BeNil())
			Expect(got.Spec.Selector.MatchLabels).To(HaveKeyWithValue("app", "sandbox-test"))

			By("Listing ops by label")
			list := &agentsv1alpha1.SandboxUpdateOpsList{}
			Expect(k8sClient.List(ctx, list, client.InNamespace(Namespace), client.MatchingLabels{"app": "e2e-test"})).To(Succeed())
			Expect(list.Items).ToNot(BeEmpty())

			By("Deleting SandboxUpdateOps")
			Expect(k8sClient.Delete(ctx, ops)).To(Succeed())

			By("Verifying deletion")
			Eventually(func() bool {
				err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      ops.Name,
					Namespace: ops.Namespace,
				}, &agentsv1alpha1.SandboxUpdateOps{})
				return errors.IsNotFound(err)
			}, time.Second*10, time.Second).Should(BeTrue())
		})
	})
})
