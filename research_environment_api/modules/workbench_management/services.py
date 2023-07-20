from typing import Iterable, Mapping

from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance
from sqlalchemy import select

from research_environment_api.modules.app import app
from research_environment_api.modules.celery_management import services
from research_environment_api.modules.workbench_management.entities import (
    GcpWorkbenchResource,
    Workbench,
)
from research_environment_api.modules.workbench_management.models import (
    WorkbenchMetadata,
)


def list_workbenches(gcp_project_id: str) -> Iterable[Workbench]:
    gcp_resources = _fetch_gcp_workbench_resources(gcp_project_id)
    if len(gcp_resources) == 0:
        return []

    workbench_metadata_dict = _fetch_workbench_metadata(gcp_resources)
    return [
        Workbench.from_gcp_resource_and_metadata(
            resource, workbench_metadata_dict[resource.id]
        )
        for resource in gcp_resources
        if resource.id in workbench_metadata_dict
    ]


def _fetch_gcp_workbench_resources(
    gcp_project_id: str,
) -> Iterable[GcpWorkbenchResource]:
    gce_instances = _fetch_gce_instances(gcp_project_id)
    app_engine_versions = _fetch_app_engine_versions(gcp_project_id)
    if len(gce_instances) and len(app_engine_versions) == 0:
        return []

    gce_instance_resources = [
        GcpWorkbenchResource.from_gce_instance(instance) for instance in gce_instances
    ]
    app_engine_resources = [
        GcpWorkbenchResource.from_app_engine_version(version)
        for version in app_engine_versions
    ]
    return gce_instance_resources + app_engine_resources


def _fetch_app_engine_versions(gcp_project_id: str) -> Iterable[AppEngineVersion]:
    app_engine_services = app.config.google_app_engine_services_client.list_services(
        {"parent": f"apps/{gcp_project_id}"}
    )
    return [
        version
        for service in app_engine_services
        for version in app.config.google_app_engine_versions_client.list_versions(
            {"parent": service.name}
        )
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


def _fetch_workbench_metadata(
    gcp_workbench_resources: Iterable[GcpWorkbenchResource],
) -> Mapping[str, Workbench]:
    gcp_identifiers = [resource.id for resource in gcp_workbench_resources]
    workbench_metadata_query = select(WorkbenchMetadata).where(
        WorkbenchMetadata.gcp_identifier.in_(gcp_identifiers)
    )
    with app.database_session() as session:
        workbench_metadata_dict = {
            metadata.gcp_identifier: metadata
            for metadata in session.scalars(workbench_metadata_query)
        }
        return workbench_metadata_dict


def create_workbench(workbench_creation_request):
    if workbench_creation_request.workbench_type == "jupyter":
        vm_image = (
            "common-cu110-notebooks"
            if workbench_creation_request.gpu_accelerator
            else "r-4-2-cpu-experimental-notebooks"
        )
        workbench_creation_request.vm_image = vm_image
        return services.create_jupyter_notebook(workbench_creation_request)
    else:
        # TODO: integrate rstuido
        pass


def stop_workbench(workbench_stop_request):
    if workbench_stop_request.workbench_type == "jupyter":
        return services.stop_jupyter_workbench(workbench_stop_request)
    else:
        # TODO: integrate rstuido
        pass
