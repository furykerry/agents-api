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
	"k8s.io/utils/ptr"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

var _ = Describe("SandboxClaim", func() {
	var (
		sandboxSet   *agentsv1alpha1.SandboxSet
		sandboxClaim *agentsv1alpha1.SandboxClaim
	)

	Context("basic claim flow", func() {
		BeforeEach(func() {
			By("Creating SandboxSet pool")
			sandboxSet = &agentsv1alpha1.SandboxSet{
				ObjectMeta: metav1.ObjectMeta{
					Name:      fmt.Sprintf("test-pool-%d", time.Now().UnixNano()),
					Namespace: Namespace,
					Labels: map[string]string{
						"app":        "e2e-test",
						"managed-by": "ginkgo",
					},
				},
				Spec: agentsv1alpha1.SandboxSetSpec{
					Replicas: int32(3),
					EmbeddedSandboxTemplate: agentsv1alpha1.EmbeddedSandboxTemplate{
						Template: basePodTemplateSpec(map[string]string{"app": "pool-test"}),
					},
				},
			}
			Expect(k8sClient.Create(ctx, sandboxSet)).To(Succeed())

			By("Verifying SandboxSet pool is created")
			Eventually(func() error {
				return k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandboxSet.Name,
					Namespace: sandboxSet.Namespace,
				}, sandboxSet)
			}, time.Second*5, time.Millisecond*500).Should(Succeed())
		})

		AfterEach(func() {
			By("Cleaning up SandboxClaim")
			if sandboxClaim != nil {
				_ = k8sClient.Delete(ctx, sandboxClaim)
			}
			By("Cleaning up SandboxSet pool")
			if sandboxSet != nil {
				_ = k8sClient.Delete(ctx, sandboxSet)
			}
		})

		It("should create SandboxClaim and verify completion", func() {
			By("Creating SandboxClaim")
			sandboxClaim = &agentsv1alpha1.SandboxClaim{
				ObjectMeta: metav1.ObjectMeta{
					Name:      fmt.Sprintf("test-sandboxclaim-%d", time.Now().UnixNano()),
					Namespace: Namespace,
					Labels: map[string]string{
						"app":        "e2e-test",
						"managed-by": "ginkgo",
					},
				},
				Spec: agentsv1alpha1.SandboxClaimSpec{
					TemplateName: sandboxSet.Name,
					Replicas:     ptr.To(int32(1)),
				},
			}
			Expect(k8sClient.Create(ctx, sandboxClaim)).To(Succeed())

			By("Verifying the SandboxClaim is created")
			Eventually(func() error {
				return k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandboxClaim.Name,
					Namespace: sandboxClaim.Namespace,
				}, sandboxClaim)
			}, time.Second*5, time.Millisecond*500).Should(Succeed())

			By("Verifying claim spec")
			Expect(sandboxClaim.Spec.TemplateName).To(Equal(sandboxSet.Name))
			Expect(*sandboxClaim.Spec.Replicas).To(Equal(int32(1)))

			By("Listing SandboxClaims by label")
			list := &agentsv1alpha1.SandboxClaimList{}
			Expect(k8sClient.List(ctx, list, client.InNamespace(Namespace), client.MatchingLabels{"app": "e2e-test"})).To(Succeed())
			Expect(list.Items).ToNot(BeEmpty())

			By("Deleting SandboxClaim")
			Expect(k8sClient.Delete(ctx, sandboxClaim)).To(Succeed())

			By("Verifying deletion")
			Eventually(func() bool {
				err := k8sClient.Get(ctx, types.NamespacedName{
					Name:      sandboxClaim.Name,
					Namespace: sandboxClaim.Namespace,
				}, &agentsv1alpha1.SandboxClaim{})
				return errors.IsNotFound(err)
			}, time.Second*10, time.Second).Should(BeTrue())
		})
	})
})
