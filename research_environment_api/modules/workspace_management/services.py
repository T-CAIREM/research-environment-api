from typing import Iterable

from google.cloud.resourcemanager_v3.types.projects import Project as GoogleProject

from research_environment_api.background import schedulers
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import (
    services as workbench_services,
)
from research_environment_api.modules.workbench_management.entities import Region
from research_environment_api.modules.workspace_management import entities


def create_workspace(workspace_creation: entities.WorkspaceCreation):
    return schedulers.create_workspace(workspace_creation)


def delete_workspace(workspace_deletion: entities.WorkspaceDeletion):
    return schedulers.destroy_workspace(workspace_deletion)


def list_active_workspaces(workspace_list_query: entities.WorkspaceListQuery):
    gcp_projects = _list_active_google_projects(workspace_list_query)

    return [_build_workspace_entity(project) for project in gcp_projects]


def _list_active_google_projects(
    workspace_list_query: entities.WorkspaceListQuery,
) -> Iterable[GoogleProject]:
    filtering_query = f"labels.cloud_identity_username:{workspace_list_query.username} lifecycleState:ACTIVE"
    return app.config.google_cloud_resource_client.search_projects(
        query=filtering_query
    ).projects


def _build_workspace_entity(gcp_project: GoogleProject) -> entities.Workspace:
    gcp_project_id = gcp_project.project_id
    region = gcp_project.labels["region"]
    billing_info = app.config.google_cloud_billing_client.get_project_billing_info(
        name=gcp_project.name
    )
    # Format: billingAccounts/<billing_account_id>
    _, billing_account_id = billing_info.billing_account_name.split("/")
    workbenches = workbench_services.list_workbenches(gcp_project_id=gcp_project_id)

    return entities.Workspace(
        gcp_project_id=gcp_project_id,
        billing_account_id=billing_account_id,
        workbenches=workbenches,
        region=Region(region),
    )
