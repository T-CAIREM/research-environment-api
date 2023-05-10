from research_environment_api.modules.logger import logger
from research_environment_api.modules.workspace_management import (
    entities,
    exceptions,
    internal,
)
from googleapiclient import errors


def create_workspace(
    google_workspace_dto: entities.GoogleWorkspaceCreation
):
    try:
        created_google_workspace = internal.create_google_workspace(google_workspace_dto)
        return created_google_workspace
    except (exceptions.GoogleProjectAlreadyExistsError, exceptions.GoogleProjectPerBillingQuotaExceededError) as error:
        if error == exceptions.GoogleProjectAlreadyExistsError:
            logger.warning(
                f"Project {google_workspace_dto.project_name} already exists"
            )
        else:
            logger.warning(
                "Projects per Billing Account quota exceeded"
            )


def list_active_workspaces(google_workspace_list_dto: entities.GoogleWorkspaceListing):
    try:
        workspaces_list = internal.list_active_workspaces(google_workspace_list_dto)
        return workspaces_list
    except errors.HttpError:
        logger.warning(
            "Google internal error occurred"
        )
