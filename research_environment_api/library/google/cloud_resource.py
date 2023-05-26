from googleapiclient.discovery import build
from google.oauth2 import service_account


class CloudResourceClient:
    def __init__(self, credentials: service_account.Credentials):
        self.cloud_resource_client = build(
            "cloudresourcemanager", "v1", credentials=credentials
        )

    def list_projects_by_name_prefix(self, project_prefix: str):
        filtering_query = f"name:{project_prefix}* lifecycleState:ACTIVE"

        workspaces_list = (
            self.cloud_resource_client.projects().list(filter=filtering_query).execute()
        )
        return workspaces_list
