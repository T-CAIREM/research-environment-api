from googleapiclient.discovery import build
from google.oauth2 import service_account


class CloudResourceClient:
    def __init__(self, credentials: service_account.Credentials):
        self.cloud_resource_client = build(
            "cloudresourcemanager", "v1", credentials=credentials
        )

    def list_projects(self, username: str):
        filtering_query = f"name:{username[:15]}* lifecycleState:ACTIVE"

        workspaces_list = (
            self.cloud_resource_client.projects().list(filter=filtering_query).execute()
        )
        return workspaces_list
