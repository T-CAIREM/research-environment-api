import random
import string
import time
from typing import Iterable, Optional, Union, List

from google.cloud import monitoring_v3, service_usage_v1
from google.cloud.resourcemanager_v3.types.projects import Project as GoogleProject
from google.cloud.service_usage_v1.types import resources

from research_environment_api.background import enums, schedulers
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.services import (
    list_workbenches,
)
from research_environment_api.modules.sharing_management.models import (
    SharingData,
    SharingState,
)
from research_environment_api.modules.sharing_management.services import (
    list_accessible_buckets_in_project,
)
from research_environment_api.modules.workspace_management import entities
from research_environment_api.modules.monitoring_management import (
    models,
    monitoring as monitoring_services,
)
from research_environment_api.web.cache import cache, QUOTAS_CACHE_TIMEOUT


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
    gcp_projects_ids = [gcp_project.project_id for gcp_project in gcp_projects]

    with app.database_session() as session:
        with session.begin():
            shared_buckets = (
                session.query(SharingData)
                .filter_by(
                    accessor_email=shared_workspace_list_query.email,
                    state=SharingState.SHARED,
                )
                .distinct(SharingData.project_id)
                .all()
            )
            session.expunge_all()

    shared_projects = [
        get_active_shared_google_project(project_id=bucket.project_id)
        for bucket in shared_buckets
        if bucket.project_id not in gcp_projects_ids
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
    filtering_query = f"labels.cloud_identity_username:{username} lifecycleState:ACTIVE parent.id:{app.config.workbenches_parent_project_id}"
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
    is_owner = gcp_project.labels["cloud_identity_username"] == caller_username
    return entities.SharedWorkspace(
        gcp_project_id=gcp_project_id,
        billing_info=billing_info_entity,
        buckets=buckets,
        status=status,
        is_owner=is_owner,
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


def list_workspace_quotas(
    workspace_list_quotas_query: entities.WorkspaceListQuotasQuery,
) -> List[entities.QuotaInfo]:
    # Initialize the clients
    project_id = workspace_list_quotas_query.workspace_project_id
    service_info = _get_service_info(project_id)
    quotas_to_list = [metric.value for metric in entities.QuotaMetrics]

    return [
        entities.QuotaInfo(
            metric_name=limit.display_name,
            limit=limit.values["DEFAULT"],
            usage=_get_current_metric_usage(
                project_id, workspace_list_quotas_query.region, limit.metric
            ),
        )
        for limit in service_info.config.quota.limits
        if limit.metric in quotas_to_list and limit.values["DEFAULT"] > 0
    ]


@cache.memoize(timeout=QUOTAS_CACHE_TIMEOUT)
def _get_service_info(project_id: str) -> resources.Service:
    client = service_usage_v1.ServiceUsageClient()
    service_name = f"projects/{project_id}/services/compute.googleapis.com"

    # Retrieve quota metrics for each enabled service
    request = service_usage_v1.GetServiceRequest(name=service_name)
    return client.get_service(request=request)


@cache.memoize(timeout=QUOTAS_CACHE_TIMEOUT)
def _get_current_metric_usage(project_id: str, region: str, metric: str) -> int:
    client = monitoring_v3.MetricServiceClient()

    # Query current usage for the given metric
    project_name = f"projects/{project_id}"
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": int(time.time())},
            "start_time": {"seconds": int(time.time()) - 604800},  # one week
        }
    )
    aggregation = monitoring_v3.Aggregation(
        alignment_period={"seconds": 60},
        cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
        per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_NEXT_OLDER,
    )
    request = monitoring_v3.ListTimeSeriesRequest(
        name=project_name,
        filter=_build_filter(project_id, region, metric),
        interval=interval,
        aggregation=aggregation,
        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
    )

    client.list_time_series(request)
    results = list(client.list_time_series(request))

    return 0 if len(results) == 0 else results[0].points[0].value.int64_value


def _build_filter(project_id: str, region: str, metric: str) -> str:
    return (
        'resource.type="consumer_quota" AND '
        'metric.type="serviceruntime.googleapis.com/quota/allocation/usage" AND '
        f'resource.label.project_id="{project_id}" AND '
        'resource.label.service="compute.googleapis.com" AND '
        f'metric.label.quota_metric="{metric}" AND '
        f'resource.label.location="{region}"'
    )


def clear_quotas_cache(project_id: str, region: str) -> None:
    for metric in entities.QuotaMetrics:
        cache.delete_memoized(
            _get_current_metric_usage, project_id, region, metric.value
        )
    cache.delete_memoized(_get_service_info, project_id)
