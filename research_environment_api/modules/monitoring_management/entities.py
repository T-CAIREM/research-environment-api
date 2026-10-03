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


# Human-readable names for the Compute Engine regional quota metrics we
# report. Keys are the metric names returned in `Region.quotas` by the
# Compute Engine Regions API.
QUOTA_METRIC_DISPLAY_NAMES = {
    "CPUS": "CPUs",
    "NVIDIA_T4_GPUS": "NVIDIA T4 GPUs",
    "INSTANCES": "VM instances",
    "IN_USE_ADDRESSES": "In-use IP addresses",
    "DISKS_TOTAL_GB": "Persistent disk total (GB)",
}


class ComputeQuotaMetric(StrEnum):
    """Base for enums whose values are Compute Engine regional quota metrics."""

    @property
    def display_name(self) -> str:
        return QUOTA_METRIC_DISPLAY_NAMES.get(self.value, self.value)


class GeneralQuotaMetrics(ComputeQuotaMetric):
    IN_USE_IP_ADDRESSES = "IN_USE_ADDRESSES"
    PERSISTENT_DISK_TOTAL = "DISKS_TOTAL_GB"
    VM_INSTANCES = "INSTANCES"
    CPUS = "CPUS"
    NVIDIA_T4_GPUS = "NVIDIA_T4_GPUS"


@dataclass
class BaseQuotaMetricsEntity:
    workspace_project_id: str


class WorkbenchUpdateQuotaMetricsEntity(ComputeQuotaMetric):
    CPUS = "CPUS"
