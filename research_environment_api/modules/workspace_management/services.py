from research_environment_api.modules.config import config
from research_environment_api.modules.workspace_management import entities
from research_environment_api.modules.workbench_management import (
    services as workbench_services,
)


def create_workspace(workspace_creation: entities.WorkspaceCreation):
    created_workspace = _create_google_project(workspace_creation)
    return created_workspace


def delete_workspace(workspace_deletion: entities.WorkspaceDeletion):
    deleted_workspace = _delete_google_project(workspace_deletion)
    return deleted_workspace


def list_active_workspaces(workspace_list_query: entities.WorkspaceListQuery):
    gcp_project_list = _list_active_google_projects(workspace_list_query)

    return [
        _build_workspace_entity(project_info)
        for project_info in gcp_project_list.get("projects", [])
    ]


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

    project_list = cloud_resource_client.list_projects_by_label(
        label="cloud_identity_username", value=workspace_list_query.username
    )
    return project_list


def _build_workspace_entity(project_info: dict) -> entities.Workspace:
    gcp_project_id = project_info["projectId"]
    workbench_list = workbench_services.list_workbenches(gcp_project_id=gcp_project_id)

    return entities.Workspace(
        gcp_project_id=gcp_project_id,
        gcp_project_number=project_info["projectNumber"],
        workbench_list=workbench_list,
    )
