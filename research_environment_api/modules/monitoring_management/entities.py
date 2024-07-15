from collections import namedtuple
from dataclasses import dataclass


WorkbenchMonitoringIdentifier = namedtuple(
    "WorkbenchMonitoringIdentifier",
    ["user_email", "dataset_identifier", "instance_type"],
)


@dataclass
class WorkbenchMonitoringDataEntry:
    user_email: str
    dataset_identifier: str
    instance_type: str
    total_time: str

    @classmethod
    def transform_workbench_monitoring_data(
        cls, identifier: WorkbenchMonitoringIdentifier, total_time: str
    ):
        return cls(
            user_email=identifier.user_email,
            dataset_identifier=identifier.dataset_identifier,
            instance_type=identifier.instance_type.value,
            total_time=total_time,
        )
