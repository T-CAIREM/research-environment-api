from research_environment_api.modules.config import config
from research_environment_api.modules.workspace_management import entities


def create_workspace(workspace_creation: entities.WorkspaceCreation):
    created_workspace = _create_google_project(workspace_creation)
    return created_workspace


def delete_workspace(workspace_deletion: entities.WorkspaceDeletion):
    deleted_workspace = _delete_google_project(workspace_deletion)
    return deleted_workspace


def list_active_workspaces(workspace_list_query: entities.WorkspaceListQuery):
    workspace_list = _list_active_google_projects(workspace_list_query)
    return workspace_list


def _create_google_project(workspace_creation: entities.WorkspaceCreation):
    workspace_controller_client = config.legacy_workspace_controller_client

    created_workspace = workspace_controller_client.create_workspace(
        gcp_user_id=workspace_creation.username,
        email=workspace_creation.email,
        region=workspace_creation.region,
        billing_account_id=workspace_creation.billing_account_id,
    )

    return created_workspace


def _delete_google_project(workspace_deletion: entities.WorkspaceDeletion):
    workspace_controller_client = config.legacy_workspace_controller_client

    created_workspace = workspace_controller_client.delete_workspace(
        gcp_project_id=workspace_deletion.workspace_id,
        gcp_user_id=workspace_deletion.username,
    )

    return created_workspace


def _list_active_google_projects(workspace_list_query: entities.WorkspaceListQuery):
    cloud_resource_client = config.google_cloud_resource_client

    project_prefix = workspace_list_query.username[:15]
    project_list = cloud_resource_client.list_projects_by_name_prefix(
        project_prefix=project_prefix
    )
    return project_list
