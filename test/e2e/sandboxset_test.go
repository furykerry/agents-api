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

var _ = Describe("SandboxSet", func() {
	var sandboxSet *agentsv1alpha1.SandboxSet

	BeforeEach(func() {
		sandboxSet = &agentsv1alpha1.SandboxSet{
			ObjectMeta: metav1.ObjectMeta{
				Name:      fmt.Sprintf("test-sandboxset-%d", time.Now().UnixNano()),
				Namespace: Namespace,
				Labels: map[string]string{
					"app":        "e2e-test",
					"managed-by": "ginkgo",
				},
			},
			Spec: agentsv1alpha1.SandboxSetSpec{
				Replicas: int32(2),
				EmbeddedSandboxTemplate: agentsv1alpha1.EmbeddedSandboxTemplate{
					Template: basePodTemplateSpec(map[string]string{"app": "sandboxset-test"}),
				},
			},
		}
	})

	AfterEach(func() {
		By("Cleaning up SandboxSet")
		_ = k8sClient.Delete(ctx, sandboxSet)
	})

	Context("creation and scale up", func() {
		It("should create SandboxSet and scale from 2 to 3 replicas", func() {
			By("Creating SandboxSet")
			Expect(k8sClient.Create(ctx, sandboxSet)).To(Succeed())

			By("Verifying the SandboxSet is created")
			Eventually(func() error {
				return k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandboxSet.Name,
					Namespace: sandboxSet.Namespace,
				}, sandboxSet)
			}, time.Second*5, time.Millisecond*500).Should(Succeed())

			By("Verifying spec.replicas is 2")
			Expect(sandboxSet.Spec.Replicas).To(Equal(int32(2)))

			By("Scaling up to 3 replicas")
			Eventually(func() error {
				if err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandboxSet.Name,
					Namespace: sandboxSet.Namespace,
				}, sandboxSet); err != nil {
					return err
				}
				sandboxSet.Spec.Replicas = int32(3)
				return k8sClient.Update(ctx, sandboxSet)
			}, time.Second*10, time.Millisecond*500).Should(Succeed())

			By("Verifying spec.replicas is updated to 3")
			Expect(k8sClient.Get(ctx, types.NamespacedName{
				Name:      sandboxSet.Name,
				Namespace: sandboxSet.Namespace,
			}, sandboxSet)).To(Succeed())
			Expect(sandboxSet.Spec.Replicas).To(Equal(int32(3)))

			By("Listing SandboxSets by label")
			list := &agentsv1alpha1.SandboxSetList{}
			Expect(k8sClient.List(ctx, list, client.InNamespace(Namespace), client.MatchingLabels{"app": "e2e-test"})).To(Succeed())
			Expect(list.Items).ToNot(BeEmpty())

			By("Deleting SandboxSet")
			Expect(k8sClient.Delete(ctx, sandboxSet)).To(Succeed())

			By("Verifying deletion")
			Eventually(func() bool {
				err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandboxSet.Name,
					Namespace: sandboxSet.Namespace,
				}, &agentsv1alpha1.SandboxSet{})
				return errors.IsNotFound(err)
			}, time.Second*10, time.Second).Should(BeTrue())
		})
	})
})
