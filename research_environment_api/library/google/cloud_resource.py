from googleapiclient.discovery import build
from google.oauth2 import service_account


class CloudResourceClient:
    def __init__(self, credentials: service_account.Credentials):
        self.cloud_resource_client = build(
            "cloudresourcemanager", "v1", credentials=credentials
        )

    def list_projects_by_label(self, label: str, value: str):
        filtering_query = f"labels.{label}:{value}"

        return self.cloud_resource_client.projects().list(filter=filtering_query).execute()
