from collections import namedtuple
from dataclasses import dataclass
from enum import StrEnum


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


@dataclass
class UsersPerDataset:
    dataset_identifier: str
    user_emails: list[str]


@dataclass
class QuotaInfo:
    metric_name: str
    limit: int
    usage: int
    region: str


@dataclass
class GeneralQuotaMetrics(StrEnum):
    IN_USE_IP_ADDRESSES = "compute.googleapis.com/regional_in_use_addresses"
    PERSISTENT_DISK_TOTAL = "compute.googleapis.com/disks_total_storage"
    VM_INSTANCES = "compute.googleapis.com/instances"
    CPUS = "compute.googleapis.com/cpus"
    NVIDIA_T4_GPUS = "compute.googleapis.com/nvidia_t4_gpus"


@dataclass
class BaseQuotaMetricsEntity:
    workspace_project_id: str


@dataclass
class WorkbenchUpdateQuotaMetricsEntity(StrEnum):
    CPUS = "compute.googleapis.com/cpus"
