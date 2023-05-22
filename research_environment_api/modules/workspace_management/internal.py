from research_environment_api.modules.workspace_management import (
    entities,
    exceptions,
)
from research_environment_api.library.google import workspace as google_workspace
from googleapiclient import errors


def create_google_workspace(google_workspace_dto: entities.GoogleWorkspaceCreation):
    try:
        created_workspace = google_workspace.create_workspace(
            region=google_workspace_dto.region,
            gcp_user_id=google_workspace_dto.username,
            billing_account_id=google_workspace_dto.billing_account_id,
        )
    except google_workspace.ProjectAlreadyExistsError:
        raise exceptions.GoogleProjectAlreadyExistsError

    return created_workspace


def list_active_workspaces(google_workspace_list_dto: entities.GoogleWorkspaceListing):
    workspaces_list = google_workspace.list_workspaces(
        username=google_workspace_list_dto.username
    )
    return workspaces_list
