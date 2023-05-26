from research_environment_api.modules.workspace_management import (
    entities,
    internal,
)


def create_workspace(google_workspace_dto: entities.WorkspaceCreation):
    created_google_workspace = internal.create_google_workspace(google_workspace_dto)
    return created_google_workspace


def list_active_workspaces(google_workspace_list_dto: entities.WorkspaceListQuery):
    workspaces_list = internal.list_active_workspaces(google_workspace_list_dto)
    return workspaces_list
