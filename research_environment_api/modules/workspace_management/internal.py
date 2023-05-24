from research_environment_api.modules.workspace_management import (
    entities,
    exceptions,
)
from research_environment_api.library.legacy_api import workspace as legacy_workspace
from research_environment_api.library.google import project as google_project
from googleapiclient import errors


def create_google_workspace(google_workspace_dto: entities.WorkspaceCreation):
    try:
        created_workspace = legacy_workspace.create_workspace(
            region=google_workspace_dto.region,
            gcp_user_id=google_workspace_dto.username,
            billing_account_id=google_workspace_dto.billing_account_id,
        )
    except legacy_workspace.ProjectAlreadyExistsError:
        raise exceptions.GoogleProjectAlreadyExistsError

    return created_workspace


def list_active_workspaces(google_workspace_list_dto: entities.WorkspaceListQuery):
    workspaces_list = google_project.list_workspaces(
        username=google_workspace_list_dto.username
    )
    return workspaces_list
