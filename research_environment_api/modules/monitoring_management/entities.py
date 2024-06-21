from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from research_environment_api.modules.app import app


@dataclass
class Timestamps:
    created_at: datetime
    deleted_at: datetime | None

    @classmethod
    def from_tuple(cls, value):
        return cls(created_at=value[0], deleted_at=value[1])


@dataclass
class WorkbenchMonitoringDataEntry:
    user_email: str
    dataset_identifier: str
    instance_type: str
    timestamps: List[Timestamps] = field(default_factory=list)
    total_time: str = field(init=False)

    def __post_init__(self):
        self.total_time = f"to be implemented"

    @classmethod
    def transform_workbench_monitoring_data(cls, key, timestamps):
        user_email = key[0]
        dataset_identifier = key[1]
        instance_type = key[2]
        values = [Timestamps.from_tuple(timestamp) for timestamp in timestamps]

        return cls(
            user_email=user_email,
            dataset_identifier=dataset_identifier,
            instance_type=instance_type.value,
            timestamps=values,
        )
