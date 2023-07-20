from typing import Iterable, Tuple

from google.cloud.appengine_admin_v1.types.service import Service as AppEngineService
from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.modules.app import app
from research_environment_api.modules.celery_management import services
from research_environment_api.modules.workbench_management.entities import Workbench
from research_environment_api.modules.workbench_management.constants import DEFAULT_APP_ENGINE_SERVICE_ID


def list_workbenches(
    gcp_project_id: str,
) -> Iterable[Workbench]:
    gce_instances = _fetch_gce_instances(gcp_project_id)
    app_engine_services = _fetch_app_engine_services(gcp_project_id)

    gce_instance_workbenches = [
        Workbench.from_gce_instance(instance) for instance in gce_instances
    ]
    app_engine_workbenches = [
        Workbench.from_app_engine_service_and_version(service, version)
        for service, version in app_engine_services
    ]
    return gce_instance_workbenches + app_engine_workbenches


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
    gce_instances_per_region = (
        app.config.google_compute_engine_instances_client.aggregated_list(
            project=gcp_project_id
        )
    )
    return [
        instance
        for region, instances_in_region in gce_instances_per_region
        for instance in instances_in_region.instances
    ]


def create_jupyter_notebook(workbench_creation_request):
    return services.create_jupyter_notebook(workbench_creation_request)


def stop_jupyter_workbench(workbench_stop_request):
    return services.stop_jupyter_workbench(workbench_stop_request)
