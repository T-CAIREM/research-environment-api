from collections import namedtuple
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

from google.cloud.appengine_admin_v1.types.service import Service as AppEngineService
from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.modules.app import app

ComputeEngineMachineResources = namedtuple(
    "ComputeEngineMachoneResources", ["cpu", "memory"]
)


MACHINE_TYPE_TO_RESOURCE_MAP = {
    "n1-standard-2": ComputeEngineMachineResources(2.0, 7.5),
    "n1-standard-4": ComputeEngineMachineResources(4.0, 15.0),
    "n1-standard-8": ComputeEngineMachineResources(8.0, 30.0),
    "n1-standard-16": ComputeEngineMachineResources(16.0, 60.0),
}


class Region(StrEnum):
    US_CENTRAL = "us-central1"
    NORTHAMERICA_NORTHEAST = "northamerica-northeast1"
    EUROPE_WEST = "europe-west3"
    AUSTRALIA_SOUTHEAST = "australia-southeast1"


class WorkbenchType(StrEnum):
    JUPYTER = "jupyter"
    RSTUDIO = "rstudio"


class WorkbenchStatus(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"


class MachineType(StrEnum):
    SMALL = "n1-standard-2"
    MEDIUM = "n1-standard-4"
    LARGE = "n1-standard-8"
    XLARGE = "n1-standard-16"


class GpuAcceleratorType(StrEnum):
    TESLA_T4 = "NVIDIA_TESLA_T4"


GCE_STATUS_MAP = {
    "RUNNING": WorkbenchStatus.RUNNING,
    "TERMINATED": WorkbenchStatus.STOPPED,
}


RSTUDIO_STATUS_MAP = {
    "SERVING": WorkbenchStatus.RUNNING,
}


@dataclass
class Workbench:
    gcp_identifier: str
    status: str
    dataset_identifier: str
    cpu: float
    memory: float
    disk_size: int
    type: WorkbenchType
    machine_type: MachineType
    region: Region
    bucket_name: str
    vm_image: str
    url: Optional[str] = None
    zone: Optional[str] = None
    gpu_accelerator_type: Optional[GpuAcceleratorType] = None

    @classmethod
    def from_gce_instance(cls, instance: ComputeEngineInstance):
        maybe_proxy_url: Optional[str] = next(
            (
                f"https://{metadata.value}"
                for metadata in instance.metadata.items
                if metadata.key == "proxy-url"
            ),
            None,
        )
        machine_type = MachineType(instance.machine_type.split("/")[-1])
        computing_resources = MACHINE_TYPE_TO_RESOURCE_MAP[machine_type]
        gpu_accelerator_type = (
            instance.guest_accelerators[0].accelerator_type
            if instance.guest_accelerators
            else None
        )
        region = instance.zone.rsplit('-', 1)[0]
        # Assume a single disk atteched to the instance.
        disk_size = instance.disks[0].disk_size_gb
        return cls(
            gcp_identifier=str(instance.id),
            dataset_identifier=instance.labels["dataset_identifier"],
            bucket_name=instance.labels["bucket_name"],
            vm_image=instance.labels["vm_image"],
            region=Region(region),
            status=GCE_STATUS_MAP[instance.status],
            cpu=computing_resources.cpu,
            memory=computing_resources.memory,
            machine_type=machine_type,
            url=maybe_proxy_url,
            zone=instance.zone,
            type=WorkbenchType.JUPYTER,
            disk_size=disk_size,
            gpu_accelerator_type=gpu_accelerator_type,
        )

    @classmethod
    def from_app_engine_service_and_version(
        cls, service: AppEngineService, version: AppEngineVersion
    ):
        return cls(
            gcp_identifier=version.id,
            dataset_identifier=service.labels["dataset_identifier"],
            status=RSTUDIO_STATUS_MAP[version.serving_status],
            cpu=version.resources.cpu,
            memory=version.resources.memory_gb,
            url=version.version_url,
            type=WorkbenchType.RSTUDIO,
        )


@dataclass
class WorkbenchCreate:
    workbench_type: str
    machine_type: MachineType
    disk_size: int
    workspace_project_id: str
    dataset_identifier: str
    user_email: str
    bucket_name: str
    region: Region
    gpu_accelerator_type: Optional[GpuAcceleratorType]
    vm_image: str = field(init=False)
    jupyter_startup_script_bucket: str = field(init=False)

    def __post_init__(self):
        self.jupyter_startup_script_bucket = app.config.jupyter_startup_script
        self.vm_image = (
            "common-cu110-notebooks"
            if self.gpu_accelerator_type
            else "r-4-2-cpu-experimental-notebooks"
        )


@dataclass
class WorkbenchUpdateDestroy:
    workbench_type: str
    workspace_project_id: str
    workbench_resource_id: str
    user_email: str
    jupyter_startup_script_bucket: str = field(init=False)

    def __post_init__(self):
        self.jupyter_startup_script_bucket = app.config.jupyter_startup_script


@dataclass
class WorkbenchToggleState:
    workbench_type: str
    workspace_project_id: str
    workbench_resource_id: str
    user_email: str
