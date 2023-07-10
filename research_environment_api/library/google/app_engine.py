from google.cloud import appengine_admin_v1
from google.oauth2 import service_account


class AppEngineClient:
    def __init__(self, credentials: service_account.Credentials):
        self.services_client = appengine_admin_v1.ServicesClient(
            credentials=credentials,
        )
        self.versions_client = appengine_admin_v1.VersionsClient(
            credentials=credentials,
        )

    def list_services(self, project: str):
        request = {"parent": f"apps/{project}"}
        return self.services_client.list_services(request=request)

    def list_versions(self, service_name: str):
        request = {
            "parent": service_name,
        }
        return self.versions_client.list_versions(request=request)
