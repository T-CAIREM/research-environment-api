from research_environment_api.modules.logger import logger
from research_environment_api.modules.workspace_management import (
    entities,
    exceptions,
    internal,
)


def create_workspace(google_workspace_dto: entities.GoogleWorkspaceCreation):
    try:
        created_google_workspace = internal.create_google_workspace(
            google_workspace_dto
        )
        return created_google_workspace
    except exceptions.GoogleProjectPerBillingQuotaExceededError as error:
        logger.warning("Projects per Billing Account quota exceeded")


def list_active_workspaces(google_workspace_list_dto: entities.GoogleWorkspaceListing):
    workspaces_list = internal.list_active_workspaces(google_workspace_list_dto)
    return workspaces_list
