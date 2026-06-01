from kubernetes import client, config
from . import Sandbox


class SandboxClient:
    def __init__(self, namespace="default"):
        self.group = "agents.kruise.io"
        self.version = "v1alpha1"
        self.plural = "sandboxes"
        self.kind = "Sandbox"
        self.namespace = namespace
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        self.api = client.CustomObjectsApi()

    def create_sandbox(self, sandbox: Sandbox) -> dict:
        sandbox.apiVersion = f"{self.group}/{self.version}"
        sandbox.kind = self.kind
        # Pydantic -> dict
        body = sandbox.model_dump(exclude_unset=True, by_alias=True)
        return self.api.create_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural=self.plural,
            body=body
        )

    def get_sandbox(self, name: str) -> dict:
        return self.api.get_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural=self.plural,
            name=name
        )

    def update_sandbox(self, name: str, body: dict) -> dict:
        return self.api.patch_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural=self.plural,
            name=name,
            body=body
        )

    def delete_sandbox(self, name: str, grace_period_seconds: int = None) -> dict:
        body = client.V1DeleteOptions()
        if grace_period_seconds is not None:
            body.grace_period_seconds = grace_period_seconds
        return self.api.delete_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace=self.namespace,
            plural=self.plural,
            name=name,
            body=body
        )
