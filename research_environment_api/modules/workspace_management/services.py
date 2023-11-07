import random
import string
from typing import Iterable, Optional, Union

from google.cloud.resourcemanager_v3.types.projects import Project as GoogleProject

from research_environment_api.background import enums, schedulers
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.services import (
    list_workbenches,
)
from research_environment_api.modules.sharing_management.models import SharingData
from research_environment_api.modules.sharing_management.services import (
    list_accessible_buckets_in_project,
)
from research_environment_api.modules.workspace_management import entities
from research_environment_api.modules.monitoring_management import (
    models,
    monitoring as monitoring_services,
)


def create_workspace(workspace_creation: entities.WorkspaceCreation):
    return schedulers.create_workspace(workspace_creation)


def delete_workspace(workspace_deletion: entities.WorkspaceDeletion):
    return schedulers.destroy_workspace(workspace_deletion)


def create_shared_workspace(
    shared_workspace_creation: entities.SharedWorkspaceCreation,
):
    return schedulers.create_shared_workspace(shared_workspace_creation)


def delete_shared_workspace(
    shared_workspace_deletion: entities.SharedWorkspaceDeletion,
):
    return schedulers.destroy_shared_workspace(shared_workspace_deletion)


def list_active_workspaces(
    workspace_list_query: entities.WorkspaceListQuery,
) -> Iterable[Union[entities.Workspace, entities.EntityScaffolding]]:
    gcp_projects = _list_active_google_projects(workspace_list_query.username)
    workflows_in_progress = monitoring_services.list_active_workflows(
        workspace_list_query.email
    )
    provisioned_workspaces = [
        _build_workspace_entity(project, workflows_in_progress)
        for project in gcp_projects
    ]
    provisioned_workspace_ids = [
        workspace.gcp_project_id for workspace in provisioned_workspaces
    ]
    workspace_scaffoldings = [
        entities.EntityScaffolding(
            id=workflow.id,
            gcp_project_id=workflow.workspace_id,
            status=entities.WorkspaceStatus.CREATING,
        )
        for workflow in workflows_in_progress
        if workflow.build_type == enums.BuildType.WORKSPACE_CREATION
        and workflow.workspace_id not in provisioned_workspace_ids
    ]
    return provisioned_workspaces + workspace_scaffoldings


def list_active_shared_workspaces(
    shared_workspace_list_query: entities.SharedWorkspaceListQuery,
) -> Iterable[Union[entities.SharedWorkspace, entities.EntityScaffolding]]:
    gcp_projects = _list_active_shared_google_projects(
        shared_workspace_list_query.username
    )
    workflows_in_progress = monitoring_services.list_active_workflows(
        shared_workspace_list_query.email
    )

    with app.database_session() as session:
        with session.begin():
            shared_buckets = (
                session.query(SharingData)
                .filter_by(
                    accessor_email=shared_workspace_list_query.email,
                )
                .distinct(SharingData.project_id)
                .all()
            )
            session.expunge_all()

    shared_projects = [
        get_active_shared_google_project(project_id=bucket.project_id)
        for bucket in shared_buckets
    ]

    accessible_workspaces = list(gcp_projects) + shared_projects

    provisioned_workspaces = [
        _build_shared_workspace_entity(
            gcp_project=project,
            workflows_in_progress=workflows_in_progress,
            caller_email=shared_workspace_list_query.email,
            caller_username=shared_workspace_list_query.username,
        )
        for project in accessible_workspaces
    ]
    provisioned_workspace_ids = [
        workspace.gcp_project_id for workspace in provisioned_workspaces
    ]
    workspace_scaffoldings = [
        entities.EntityScaffolding(
            id=workflow.id,
            gcp_project_id=workflow.workspace_id,
            status=entities.WorkspaceStatus.CREATING,
        )
        for workflow in workflows_in_progress
        if workflow.build_type == enums.BuildType.SHARED_WORKSPACE_CREATION
        and workflow.workspace_id not in provisioned_workspace_ids
    ]
    return provisioned_workspaces + workspace_scaffoldings


def _filter_google_projects(filtering_query: str) -> Iterable[GoogleProject]:
    return app.config.google_cloud_resource_client.search_projects(
        query=filtering_query
    ).projects


def _list_active_google_projects(
    username: str,
) -> Iterable[GoogleProject]:
    filtering_query = f"labels.cloud_identity_username:{username} lifecycleState:ACTIVE"
    return _filter_google_projects(filtering_query)


def _list_active_shared_google_projects(
    username: str,
) -> Iterable[GoogleProject]:
    filtering_query = f"labels.cloud_identity_username:{username} lifecycleState:ACTIVE labels.type:data-sharing"
    return _filter_google_projects(filtering_query)


def get_active_google_project(
    project_id: str,
    username: str,
) -> GoogleProject:
    filtering_query = f"id:{project_id} labels.cloud_identity_username:{username} lifecycleState:ACTIVE"
    return _filter_google_projects(filtering_query)[0]


def get_active_shared_google_project(
    project_id: str,
) -> GoogleProject:
    filtering_query = f"id:{project_id} lifecycleState:ACTIVE labels.type:data-sharing"
    return _filter_google_projects(filtering_query)[0]


def _build_workspace_entity(
    gcp_project: GoogleProject,
    workflows_in_progress: Iterable[models.WorkbenchActivity],
) -> entities.Workspace:
    gcp_project_id = gcp_project.project_id
    region = gcp_project.labels["region"]
    billing_info_entity = _build_billing_entity(gcp_project.name)
    workbenches = list_workbenches(
        gcp_project_id=gcp_project_id, workflows_in_progress=workflows_in_progress
    )
    workspace_workflow_in_progress = _match_workspace_workflow(
        gcp_project_id, workflows_in_progress
    )
    status = (
        entities.WORKSPACE_ACTIVITY_TYPE_MAP[workspace_workflow_in_progress.build_type]
        if workspace_workflow_in_progress
        else entities.WorkspaceStatus.CREATED
    )
    return entities.Workspace(
        gcp_project_id=gcp_project_id,
        billing_info=billing_info_entity,
        workbenches=workbenches,
        region=entities.Region(region),
        status=status,
    )


def _build_shared_workspace_entity(
    gcp_project: GoogleProject,
    workflows_in_progress: Iterable[models.WorkbenchActivity],
    caller_email: str,
    caller_username: str,
) -> entities.SharedWorkspace:
    gcp_project_id = gcp_project.project_id
    billing_info_entity = _build_billing_entity(gcp_project.name)
    buckets = list_accessible_buckets_in_project(
        gcp_project_id=gcp_project_id,
        username=caller_username,
        caller_email=caller_email,
    )
    workspace_workflow_in_progress = _match_workspace_workflow(
        gcp_project_id, workflows_in_progress
    )
    status = (
        entities.WORKSPACE_ACTIVITY_TYPE_MAP[workspace_workflow_in_progress.build_type]
        if workspace_workflow_in_progress
        else entities.WorkspaceStatus.CREATED
    )
    return entities.SharedWorkspace(
        gcp_project_id=gcp_project_id,
        billing_info=billing_info_entity,
        buckets=buckets,
        status=status,
    )


def _build_billing_entity(project_name: str):
    billing_info = app.config.google_cloud_billing_client.get_project_billing_info(
        name=project_name
    )
    raw_billing_account_name = billing_info.billing_account_name
    # Format: billingAccounts/<billing_account_id>
    if raw_billing_account_name:
        _, raw_billing_account_name = billing_info.billing_account_name.split("/")

    billing_info_entity = entities.BillingInfo(
        billing_account_id=raw_billing_account_name,
        billing_enabled=billing_info.billing_enabled,
    )
    return billing_info_entity


def _match_workspace_workflow(
    gcp_project_id: str, workflows_in_progress: Iterable[models.WorkbenchActivity]
) -> Optional[models.WorkbenchActivity]:
    return next(
        filter(
            lambda workflow: workflow.workspace_id == gcp_project_id
            and workflow.build_type
            in [
                enums.BuildType.WORKSPACE_CREATION,
                enums.BuildType.WORKSPACE_DELETION,
                enums.BuildType.SHARED_WORKSPACE_CREATION,
                enums.BuildType.SHARED_WORKSPACE_DELETION,
            ],
            workflows_in_progress,
        ),
        None,
    )


def generate_resource_name_from_dataset_identifier(dataset_identifier: str) -> str:
    return f"{dataset_identifier[:15]}-{''.join(random.choices(string.ascii_lowercase, k=5))}"
