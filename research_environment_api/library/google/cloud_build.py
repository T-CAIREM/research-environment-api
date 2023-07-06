from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account


class CloudBuildClient:
    def __init__(self, credentials: service_account.Credentials):
        self.cloud_build_client = cloudbuild_v1.services.cloud_build.CloudBuildClient(
            credentials=credentials
        )

    def create_cloud_build(self, build: cloudbuild_v1.Build, project_id: str):
        operation = self.cloud_build_client.create_build(
            project_id=project_id, build=build
        )
        return operation

    def get_cloud_build_information(self, project_id: str, build_id: str):
        build_information = self.cloud_build_client.get_build(
            project_id=project_id, id=build_id
        )
        return build_information
