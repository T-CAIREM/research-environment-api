from typing import Self, Optional
from dataclasses import dataclass

from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.modules.workbench_management.models import (
    WorkbenchMetadata,
)


@dataclass
class Workbench:
    gcp_identifier: str
    zone: str
    instance_status: str
    dataset_slug: str
    dataset_version: str
    instance_status_message: Optional[str]

    @classmethod
    def from_gce_instance_and_metadata(
        cls, instance: ComputeEngineInstance, metadata: WorkbenchMetadata
    ) -> Self:
        return cls(
            gcp_identifier=instance.id,
            zone=instance.zone,
            instance_status=instance.status,
            dataset_slug=metadata.dataset_slug,
            dataset_version=metadata.dataset_version,
            instance_status_message=instance.status_message,
        )
