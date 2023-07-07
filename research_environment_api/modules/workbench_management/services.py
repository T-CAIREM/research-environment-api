from typing import Mapping, Iterable

from sqlalchemy import select
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.modules.db import make_session
from research_environment_api.modules.config import config
from research_environment_api.modules.workbench_management.entities import Workbench
from research_environment_api.modules.workbench_management.models import (
    WorkbenchMetadata,
)


def list_workbenches(gcp_project_id: str):
    gce_instances = _fetch_gce_instances(gcp_project_id)
    instance_identifiers = [instance.id for instance in gce_instances]
    workbench_metadata_dict = _fetch_workbench_metadata(instance_identifiers)

    return [
        Workbench.from_gce_instance(
            instance, workbench_metadata_dict[instance.gcp_identifier]
        )
        for instance in gce_instances
    ]


def _fetch_gce_instances(gcp_project_id: str) -> ComputeEngineInstance:
    compute_engine_client = config.google_compute_engine_client
    gce_instances_per_region = compute_engine_client.list_instances(
        project=gcp_project_id
    )
    return [
        instance
        for region, instances_in_region in gce_instances_per_region
        for instance in instances_in_region.instances
    ]


def _fetch_workbench_metadata(
    instance_identifiers: Iterable[str],
) -> Mapping[str, Workbench]:
    workbench_metadata_query = select(WorkbenchMetadata).where(
        WorkbenchMetadata.gcp_identifier.in_(instance_identifiers)
    )
    with make_session() as session:
        workbench_metadata_dict = {
            metadata.gcp_identifier: metadata
            for metadata in session.scalars(workbench_metadata_query)
        }
        return workbench_metadata_dict
