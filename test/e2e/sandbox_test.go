package e2e

import (
	"fmt"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	agentsv1alpha1 "github.com/openkruise/agents-api/agents/v1alpha1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

var _ = Describe("Sandbox", func() {
	var sandbox *agentsv1alpha1.Sandbox

	BeforeEach(func() {
		sandbox = &agentsv1alpha1.Sandbox{
			ObjectMeta: metav1.ObjectMeta{
				Name:      fmt.Sprintf("test-sandbox-%d", time.Now().UnixNano()),
				Namespace: Namespace,
				Labels: map[string]string{
					"app":        "e2e-test",
					"managed-by": "ginkgo",
				},
			},
			Spec: agentsv1alpha1.SandboxSpec{
				EmbeddedSandboxTemplate: agentsv1alpha1.EmbeddedSandboxTemplate{
					Template: basePodTemplateSpec(map[string]string{"app": "sandbox-test"}),
				},
			},
		}
	})

	AfterEach(func() {
		By("Cleaning up Sandbox")
		_ = k8sClient.Delete(ctx, sandbox)
	})

	Context("CRUD operations", func() {
		It("should create, get, update, list, and delete sandbox", func() {
			By("Creating Sandbox")
			Expect(k8sClient.Create(ctx, sandbox)).To(Succeed())

			By("Verifying the sandbox is created")
			Eventually(func() error {
				return k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandbox.Name,
					Namespace: sandbox.Namespace,
				}, sandbox)
			}, time.Second*5, time.Millisecond*500).Should(Succeed())

			By("Updating labels")
			Eventually(func() error {
				if err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandbox.Name,
					Namespace: sandbox.Namespace,
				}, sandbox); err != nil {
					return err
				}
				sandbox.Labels["updated"] = "true"
				return k8sClient.Update(ctx, sandbox)
			}, time.Second*10, time.Millisecond*500).Should(Succeed())

			By("Listing Sandboxes by label")
			list := &agentsv1alpha1.SandboxList{}
			Expect(k8sClient.List(ctx, list, client.InNamespace(Namespace), client.MatchingLabels{"app": "e2e-test"})).To(Succeed())
			Expect(list.Items).ToNot(BeEmpty())

			By("Deleting Sandbox")
			Expect(k8sClient.Delete(ctx, sandbox)).To(Succeed())

			By("Verifying deletion")
			Eventually(func() bool {
				err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandbox.Name,
					Namespace: sandbox.Namespace,
				}, &agentsv1alpha1.Sandbox{})
				return errors.IsNotFound(err)
			}, time.Second*10, time.Second).Should(BeTrue())
		})
	})
})
