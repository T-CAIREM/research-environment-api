from typing import Iterable, Tuple

from google.cloud.appengine_admin_v1.types.service import Service as AppEngineService
from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.background import schedulers
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import entities

DEFAULT_APP_ENGINE_SERVICE_ID = "default"


def list_workbenches(
    gcp_project_id: str,
) -> Iterable[entities.Workbench]:
    gce_instances = _fetch_gce_instances(gcp_project_id)
    app_engine_services = _fetch_app_engine_services(gcp_project_id)

    gce_instance_workbenches = [
        entities.Workbench.from_gce_instance(instance) for instance in gce_instances
    ]
    app_engine_workbenches = [
        entities.Workbench.from_app_engine_service_and_version(service, version)
        for service, version in app_engine_services
    ]
    return gce_instance_workbenches + app_engine_workbenches


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
    workbench_creation_request: entities.WorkbenchCreate,
):
    if workbench_creation_request.workbench_type == "jupyter":
        return schedulers.create_jupyter_workbench(workbench_creation_request)
    else:
        return schedulers.create_rstudio_workbench(workbench_creation_request)


def schedule_workbench_stop(workbench_stop_request: entities.WorkbenchToggleState):
    if workbench_stop_request.workbench_type == "jupyter":
        return schedulers.stop_jupyter_workbench(workbench_stop_request)
    else:
        return schedulers.stop_rstudio_workbench(workbench_stop_request)


def schedule_workbench_start(workbench_start_request: entities.WorkbenchToggleState):
    if workbench_start_request.workbench_type == "jupyter":
        return schedulers.start_jupyter_workbench(workbench_start_request)
    else:
        return schedulers.start_rstudio_workbench(workbench_start_request)
    pass


def schedule_workbench_update(
    workbench_update_request: entities.WorkbenchUpdateDestroy,
):
    if workbench_update_request.workbench_type == "jupyter":
        return schedulers.update_jupyter_workbench(workbench_update_request)
    else:
        return schedulers.update_rstudio_workbench(workbench_update_request)


def schedule_workbench_destroy(
    workbench_destroy_request: entities.WorkbenchUpdateDestroy,
):
    if workbench_destroy_request.workbench_type == "jupyter":
        return schedulers.destroy_jupyter_workbench(workbench_destroy_request)
    else:
        schedulers.destroy_rstudio_workbench(workbench_destroy_request)
