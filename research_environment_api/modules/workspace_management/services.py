from research_environment_api.modules.workspace_management import (
    entities,
    internal,
)


def create_workspace(workspace_creation: entities.WorkspaceCreation):
    created_workspace = internal.create_google_project(workspace_creation)
    return created_workspace


def delete_workspace(workspace_deletion: entities.WorkspaceDeletion):
    deleted_workspace = internal.delete_google_project(workspace_deletion)
    return deleted_workspace


def list_active_workspaces(workspace_list_query: entities.WorkspaceListQuery):
    workspace_list = internal.list_active_google_projects(workspace_list_query)
    return workspace_list
