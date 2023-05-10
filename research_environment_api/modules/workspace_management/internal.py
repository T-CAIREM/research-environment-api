from research_environment_api.modules.workspace_management import (
    entities,
    exceptions,
)
from research_environment_api.library.google import workspace as google_workspace
from googleapiclient import errors


def create_google_workspace(google_workspace_dto: entities.GoogleWorkspaceCreation):
    try:
        created_workspace = google_workspace.create_workspace(
            region=google_workspace_dto.region.name,
            project_name=google_workspace_dto.project_name
        )
    except google_workspace.ProjectAlreadyExistsError:
        raise exceptions.GoogleProjectAlreadyExistsError

    try:
        google_workspace.attach_billing_to_project(
            project_name=google_workspace_dto.project_name,
            billing_account_resource_name=google_workspace_dto.billing_account_resource_name
        )
    except google_workspace.ProjectsPerBillingAccountExceededError:
        raise exceptions.GoogleProjectPerBillingQuotaExceededError

    return created_workspace


def list_active_workspaces(google_workspace_list_dto: entities.GoogleWorkspaceListing):
    try:
        workspaces_list = google_workspace.list_workspaces(
            family_name=google_workspace_list_dto.family_name
        )
        return workspaces_list
    except errors.HttpError as error:
        raise error
