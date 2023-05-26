from research_environment_api.modules import config
from research_environment_api.modules.workspace_management import (
    entities,
)


def create_google_project(workspace_creation: entities.WorkspaceCreation):
    workspace_controller_client = config.app_config().legacy_workspace_controller_client

    created_workspace = workspace_controller_client.create_workspace(
        region=workspace_creation.region,
        gcp_user_id=workspace_creation.username,
        billing_account_id=workspace_creation.billing_account_id,
    )

    return created_workspace


def list_active_google_projects(workspace_list_query: entities.WorkspaceListQuery):
    cloud_resource_client = config.app_config().google_cloud_resource_client

    project_prefix = workspace_list_query.username[:15]
    project_list = cloud_resource_client.list_projects_by_name_prefix(
        project_prefix=project_prefix
    )
    return project_list
