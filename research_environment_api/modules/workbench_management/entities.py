from typing import Self, Optional
from dataclasses import dataclass

from google.cloud.compute_v1.types.compute import ComputeEngineInstance


@dataclass
class Workbench:
    gcp_identifier: str
    zone: str
    instance_status: str
    instance_status_message: Optional[str]

    @classmethod
    def from_gce_instance(cls, instance: ComputeEngineInstance) -> Self:
        return cls(
            gcp_identifier=instance.id,
            zone=instance.zone,
            instance_status=instance.status,
            instance_status_message=instance.status_message,
        )
