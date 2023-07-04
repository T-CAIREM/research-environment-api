from google.cloud import compute_v1
from google.oauth2 import service_account


class ComputeEngineClient:
    def __init__(self, credentials: service_account.Credentials):
        self.instances_client = compute_v1.InstancesClient(credentials=credentials)

    def list_instances(self, project: str):
        return self.instances_client.aggregated_list(project=project)
