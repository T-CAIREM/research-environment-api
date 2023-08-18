from typing import Iterable, Tuple, Union

from google.cloud.appengine_admin_v1.types.service import Service as AppEngineService
from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance
from google.cloud.resourcemanager_v3.types.projects import Project as GoogleProject

from research_environment_api.background import schedulers, enums
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import (
    entities,
    models,
    monitoring as monitoring_services,
)

DEFAULT_APP_ENGINE_SERVICE_ID = "default"


def create_workspace(workspace_creation: entities.WorkspaceCreation):
    return schedulers.create_workspace(workspace_creation)


def delete_workspace(workspace_deletion: entities.WorkspaceDeletion):
    return schedulers.destroy_workspace(workspace_deletion)


def list_active_workspaces(
    workspace_list_query: entities.WorkspaceListQuery,
) -> Iterable[Union[entities.Workspace, entities.GoogleEntityScaffolding]]:
    gcp_projects = _list_active_google_projects(workspace_list_query.username)
    workflows_in_progress = monitoring_services.list_active_workflows(
        workspace_list_query.email
    )
    build_scaffolding = [
        entities.GoogleEntityScaffolding(workflow.workspace_id)
        for workflow in workflows_in_progress
        if workflow.build_type == enums.BuildType.WORKSPACE_CREATION
    ]
    return [
        _build_workspace_entity(project, workflows_in_progress)
        for project in gcp_projects
    ] + build_scaffolding


def _filter_google_projects(filtering_query: str) -> Iterable[GoogleProject]:
    return app.config.google_cloud_resource_client.search_projects(
        query=filtering_query
    ).projects


def _list_active_google_projects(
    username: str,
) -> Iterable[GoogleProject]:
    filtering_query = f"labels.cloud_identity_username:{username} lifecycleState:ACTIVE"
    return _filter_google_projects(filtering_query)


def get_active_google_project(
    project_id: str,
    username: str,
) -> GoogleProject:
    filtering_query = f"id:{project_id} labels.cloud_identity_username:{username} lifecycleState:ACTIVE"
    return _filter_google_projects(filtering_query)[0]


def _build_workspace_entity(
    gcp_project: GoogleProject,
    workflows_in_progress: Iterable[models.WorkbenchActivity],
) -> entities.Workspace:
    gcp_project_id = gcp_project.project_id
    region = gcp_project.labels["region"]
    billing_info = app.config.google_cloud_billing_client.get_project_billing_info(
        name=gcp_project.name
    )
    raw_billing_account_name = billing_info.billing_account_name
    # Format: billingAccounts/<billing_account_id>
    if raw_billing_account_name:
        _, raw_billing_account_name = billing_info.billing_account_name.split("/")

    billing_info_entity = entities.BillingInfo(
        billing_account_id=raw_billing_account_name,
        billing_enabled=billing_info.billing_enabled,
    )
    workbenches = list_workbenches(
        gcp_project_id=gcp_project_id, workflows_in_progress=workflows_in_progress
    )
    workspace_workflow_in_progress = _match_workspace_workflow(
        gcp_project_id, workflows_in_progress
    )
    return entities.Workspace(
        gcp_project_id=gcp_project_id,
        billing_info=billing_info_entity,
        workbenches=workbenches,
        region=entities.Region(region),
        workflow_in_progress=workspace_workflow_in_progress,
    )


def _match_workspace_workflow(
    gcp_project_id: str, workflows_in_progress: Iterable[models.WorkbenchActivity]
):
    return next(
        filter(
            lambda workflow: workflow.workspace_id == gcp_project_id,
            workflows_in_progress,
        ),
        None,
    )


def list_workbenches(
    gcp_project_id: str,
    workflows_in_progress: Iterable[models.WorkbenchActivity],
) -> Iterable[Union[entities.Workbench, entities.GoogleEntityScaffolding]]:
    gce_instances = _fetch_gce_instances(gcp_project_id)
    app_engine_services = _fetch_app_engine_services(gcp_project_id)

    gce_instance_workbenches = [
        entities.Workbench.from_gce_instance(instance, workflows_in_progress)
        for instance in gce_instances
    ]
    app_engine_workbenches = [
        entities.Workbench.from_app_engine_service_and_version(service, version)
        for service, version in app_engine_services
    ]

    workbench_scaffolding = [
        entities.GoogleEntityScaffolding(gcp_project_id=workflow.workspace_id)
        for workflow in workflows_in_progress
        if workflow.workspace_id == gcp_project_id
        and workflow.build_type == enums.BuildType.JUPYTER_CREATION
    ]
    return gce_instance_workbenches + app_engine_workbenches + workbench_scaffolding


def get_jupyter_workbench(
    gcp_project_id: str,
    workbench_resource_id: str,
) -> entities.Workbench:
    # The API exposes instance IDs as strings for compatibility reasons.
    instance_id = int(workbench_resource_id)
    gce_instances = _fetch_gce_instances(gcp_project_id)
    gce_instance = next(
        filter(lambda instance: instance.id == instance_id, gce_instances)
    )
    return entities.Workbench.from_gce_instance(gce_instance)


def _fetch_app_engine_services(
    gcp_project_id: str,
) -> Iterable[Tuple[AppEngineService, AppEngineVersion]]:
    app_engine_services = app.config.google_app_engine_services_client.list_services(
        {"parent": f"apps/{gcp_project_id}"}
    )
    return [
        (service, version)
        for service in app_engine_services
        for version in app.config.google_app_engine_versions_client.list_versions(
            {"parent": service.name}
        )
        if service.id != DEFAULT_APP_ENGINE_SERVICE_ID
    ]


def _fetch_gce_instances(gcp_project_id: str) -> Iterable[ComputeEngineInstance]:
    gce_instances_per_zone = (
        app.config.google_compute_engine_instances_client.aggregated_list(
            project=gcp_project_id
        )
    )
    return [
        instance
        for zone, instances_in_region in gce_instances_per_zone
        for instance in instances_in_region.instances
    ]


def schedule_workbench_create(
    workbench_creation: entities.WorkbenchCreate,
):
    if workbench_creation.workbench_type == "jupyter":
        return schedulers.create_jupyter_workbench(workbench_creation)
    else:
        # TODO: Integrate RStudio
        pass


def schedule_workbench_stop(workbench_stop_request: entities.WorkbenchToggleState):
    if workbench_stop_request.workbench_type == "jupyter":
        return schedulers.stop_jupyter_workbench(workbench_stop_request)
    else:
        # TODO: Integrate RStudio
        pass


def schedule_workbench_start(workbench_start_request: entities.WorkbenchToggleState):
    if workbench_start_request.workbench_type == "jupyter":
        return schedulers.start_jupyter_workbench(workbench_start_request)
    else:
        # TODO: Integrate RStudio
        pass
    pass


def schedule_workbench_update(
    workbench_update_request: entities.WorkbenchUpdate,
):
    if workbench_update_request.workbench_type == "jupyter":
        return schedulers.update_jupyter_workbench(workbench_update_request)
    else:
        # TODO: Integrate RStudio
        pass


def schedule_workbench_destroy(
    workbench_destroy_request: entities.WorkbenchDestroy,
):
    if workbench_destroy_request.workbench_type == "jupyter":
        return schedulers.destroy_jupyter_workbench(workbench_destroy_request)
    else:
        # TODO: Integrate RStudio
        pass
