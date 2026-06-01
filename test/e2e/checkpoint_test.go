package e2e

import (
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	agentsv1alpha1 "github.com/openkruise/agents-api/agents/v1alpha1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/utils/ptr"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

var _ = Describe("Checkpoint", func() {
	Context("CRUD operations", func() {
		var checkpointName string

		BeforeEach(func() {
			checkpointName = generateTestName("test-checkpoint")
		})

		AfterEach(func() {
			By("Cleaning up Checkpoint")
			cp := &agentsv1alpha1.Checkpoint{
				ObjectMeta: metav1.ObjectMeta{
					Name:      checkpointName,
					Namespace: Namespace,
				},
			}
			_ = k8sClient.Delete(ctx, cp)
		})

		It("should create, get, list, and delete a Checkpoint", func() {
			sandboxName := "test-sandbox"
			podName := "test-pod"

			By("Creating Checkpoint")
			checkpoint := &agentsv1alpha1.Checkpoint{
				ObjectMeta: metav1.ObjectMeta{
					Name:      checkpointName,
					Namespace: Namespace,
					Labels: map[string]string{
						"app":        "e2e-test",
						"managed-by": "ginkgo",
					},
				},
				Spec: agentsv1alpha1.CheckpointSpec{
					SandboxName: ptr.To(sandboxName),
					PodName:     ptr.To(podName),
				},
			}
			Expect(k8sClient.Create(ctx, checkpoint)).To(Succeed())

			By("Getting and verifying spec")
			got := &agentsv1alpha1.Checkpoint{}
			Expect(k8sClient.Get(ctx, client.ObjectKey{Name: checkpointName, Namespace: Namespace}, got)).To(Succeed())
			Expect(got.Spec.SandboxName).ToNot(BeNil())
			Expect(*got.Spec.SandboxName).To(Equal(sandboxName))
			Expect(got.Spec.PodName).ToNot(BeNil())
			Expect(*got.Spec.PodName).To(Equal(podName))

			By("Listing by label")
			list := &agentsv1alpha1.CheckpointList{}
			Expect(k8sClient.List(ctx, list, client.InNamespace(Namespace), client.MatchingLabels{"app": "e2e-test"})).To(Succeed())
			Expect(list.Items).ToNot(BeEmpty())

			By("Deleting Checkpoint")
			Expect(k8sClient.Delete(ctx, checkpoint)).To(Succeed())

			By("Verifying deletion")
			Eventually(func() bool {
				err := k8sClient.Get(ctx, client.ObjectKey{Name: checkpointName, Namespace: Namespace}, &agentsv1alpha1.Checkpoint{})
				return errors.IsNotFound(err)
			}, time.Second*10, time.Second).Should(BeTrue())
		})
	})
})
