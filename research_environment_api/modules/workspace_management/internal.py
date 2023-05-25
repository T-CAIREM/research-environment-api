from research_environment_api.modules import config
from research_environment_api.modules.workspace_management import (
    entities,
)


def create_google_workspace(google_workspace_dto: entities.WorkspaceCreation):
    workspace_controller_client = config.app_config().legacy_workspace_controller_client

    created_workspace = workspace_controller_client.create_workspace(
        region=google_workspace_dto.region,
        gcp_user_id=google_workspace_dto.username,
        billing_account_id=google_workspace_dto.billing_account_id,
    )

    return created_workspace


def list_active_workspaces(google_workspace_list_dto: entities.WorkspaceListQuery):
    cloud_resource_client = config.app_config().google_cloud_resource_client

    workspaces_list = cloud_resource_client.list_workspaces(
        username=google_workspace_list_dto.username
    )
    return workspaces_list
