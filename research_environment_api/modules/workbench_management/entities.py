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
        metadata = {item.key: item.value for item in instance.metadata.items}
        print(metadata)

        maybe_proxy_url: Optional[str] = (
            f"https://{metadata.get('proxy-url')}"
            if metadata.get("proxy-url")
            else None
        )
        dataset_identifier = metadata["dataset_identifier"]
        bucket_name = metadata["bucket_name"]
        vm_image = metadata["vm_image"]
        machine_type = MachineType(instance.machine_type.split("/")[-1])
        computing_resources = MACHINE_TYPE_TO_RESOURCE_MAP[machine_type]
        gpu_accelerator_type = (
            instance.guest_accelerators[0].accelerator_type
            if instance.guest_accelerators
            else None
        )
        zone = instance.zone.split("/")[-1]
        region = zone.rsplit("-", 1)[0]
        # Assume a single disk atteched to the instance.
        disk_size = instance.disks[0].disk_size_gb
        return cls(
            gcp_identifier=str(instance.id),
            dataset_identifier=dataset_identifier,
            bucket_name=bucket_name,
            vm_image=vm_image,
            region=Region(region),
            status=GCE_STATUS_MAP[instance.status],
            cpu=computing_resources.cpu,
            memory=computing_resources.memory,
            machine_type=machine_type,
            url=maybe_proxy_url,
            zone=zone,
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
class BaseWorkbenchEntity:
    workbench_type: str
    workspace_project_id: str
    user_email: str


@dataclass
class WorkbenchCreate(BaseWorkbenchEntity):
    machine_type: MachineType
    disk_size: int
    dataset_identifier: str
    bucket_name: str
    region: Region
    gpu_accelerator_type: Optional[GpuAcceleratorType] = None
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
class WorkbenchDestroy(BaseWorkbenchEntity):
    workbench_resource_id: str
    jupyter_startup_script_bucket: str = field(init=False)

    def __post_init__(self):
        self.jupyter_startup_script_bucket = app.config.jupyter_startup_script


class WorkbenchUpdate(BaseWorkbenchEntity):
    machine_type: MachineType
    workbench_resource_id: str
    jupyter_startup_script_bucket: str = field(init=False)

    def __post_init__(self):
        self.jupyter_startup_script_bucket = app.config.jupyter_startup_script


@dataclass
class WorkbenchToggleState:
    workbench_type: str
    workspace_project_id: str
    workbench_resource_id: str
    user_email: str
