import random
from copy import deepcopy
from typing import Iterable, Mapping

from celery import chain
from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance
from sqlalchemy import select

from research_environment_api.modules.config import config
from research_environment_api.modules.db import make_session
from research_environment_api.modules.workbench_management import (
    enums,
    factories,
    tasks,
)
from research_environment_api.modules.workbench_management.constants import (
    AVAILABLE_ZONES,
)
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
    app_engine_services = config.google_app_engine_services_client.list_services(
        {"parent": f"apps/{gcp_project_id}"}
    )
    return [
        version
        for service in app_engine_services
        for version in config.google_app_engine_versions_client.list_versions(
            {"parent": service.name}
        )
    ]


def _fetch_gce_instances(gcp_project_id: str) -> Iterable[ComputeEngineInstance]:
    gce_instances_per_region = (
        config.google_compute_engine_instances_client.aggregated_list(
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
    with make_session() as session:
        workbench_metadata_dict = {
            metadata.gcp_identifier: metadata
            for metadata in session.scalars(workbench_metadata_query)
        }
        return workbench_metadata_dict


def start_jupyter_notebook(workbench_creation_request):
    zone, available_zones = _get_available_zones(workbench_creation_request.region)

    build = factories.BuildFactory(
        config.project_id, _create_cloud_build_source()
    ).create_jupyter(
        machine_type=workbench_creation_request.machine_type,
        user_project_id=workbench_creation_request.user_project_id,
        dataset=workbench_creation_request.dataset,
        email_id=workbench_creation_request.email_id,
        bucket_name=workbench_creation_request.bucket_name,
        region=workbench_creation_request.region,
        persistent_disk=workbench_creation_request.persistent_disk,
        gpu_accelerator=workbench_creation_request.gpu_accelerator,
        vm_image=workbench_creation_request.vm_image,
        zone=zone,
        jupyter_startup_script_bucket=workbench_creation_request.jupyter_startup_script_bucket,
    )
    return chain(
        tasks.start_cloud_build.s(
            build=build, build_type=enums.BuildType.JUPYTER_CREATION
        ),
        tasks.check_cloud_build_status.s(),
        tasks.handle_jupyter_workbench_build_error.s(available_zones, build),
    )()


def _create_cloud_build_source():
    return {
        "repo_source": {
            "project_id": config.project_id,
            "repo_name": config.terraform_repo_name,
            "branch_name": config.terraform_branch_name,
        }
    }


def _get_available_zones(region: str):
    available_zones = deepcopy(AVAILABLE_ZONES[region])
    random.shuffle(available_zones)
    return available_zones.pop(0), available_zones
