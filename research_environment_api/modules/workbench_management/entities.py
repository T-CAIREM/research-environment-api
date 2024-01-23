from collections import namedtuple
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable, Optional, List

from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.background.enums import BuildType
from research_environment_api.modules.app import app
from research_environment_api.modules.monitoring_management import models

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
    STOPPING = "stopping"
    UPDATING = "updating"
    DESTROYING = "destroying"
    CREATING = "creating"
    STARTING = "starting"


class MachineType(StrEnum):
    SMALL = "n1-standard-2"
    MEDIUM = "n1-standard-4"
    LARGE = "n1-standard-8"
    XLARGE = "n1-standard-16"


class GpuAcceleratorType(StrEnum):
    TESLA_T4 = "NVIDIA_TESLA_T4"


GCE_STATUS_MAP = {
    "RUNNING": WorkbenchStatus.RUNNING,
    # There's a brief moment where, after the workflow is finished, a GCE instance has the STAGING status
    "STAGING": WorkbenchStatus.RUNNING,
    "TERMINATED": WorkbenchStatus.STOPPED,
}

WORKBENCH_ACTIVITY_TYPE_MAP = {
    BuildType.WORKBENCH_CREATION: WorkbenchStatus.CREATING,
    BuildType.WORKBENCH_DESTROY: WorkbenchStatus.DESTROYING,
    BuildType.WORKBENCH_STOP: WorkbenchStatus.STOPPING,
    BuildType.WORKBENCH_START: WorkbenchStatus.STARTING,
    BuildType.WORKBENCH_UPDATE: WorkbenchStatus.UPDATING,
}


RSTUDIO_STATUS_MAP = {
    "SERVING": WorkbenchStatus.RUNNING,
    "STOPPED": WorkbenchStatus.STOPPED,
}


@dataclass
class Workbench:
    id: str
    resource_id: str
    status: WorkbenchStatus
    dataset_identifier: str
    cpu: float
    memory: float
    disk_size: int
    type: WorkbenchType
    machine_type: MachineType
    region: Region
    bucket_name: str
    vm_image: str
    service_account_name: str
    brand_name: Optional[str] = None
    url: Optional[str] = None
    zone: Optional[str] = None
    gpu_accelerator_type: Optional[GpuAcceleratorType] = None
    sharing_bucket_identifiers: List[str] = field(default_factory=list)

    @classmethod
    def from_gce_instance(
        cls,
        instance: ComputeEngineInstance,
        workflows_in_progress: Iterable[models.WorkbenchActivity],
    ):
        metadata = {item.key: item.value for item in instance.metadata.items}

        maybe_proxy_url: Optional[str] = (
            f"https://{metadata.get('proxy-url')}"
            if metadata.get("proxy-url")
            else None
        )
        dataset_identifier = metadata["dataset_identifier"]
        bucket_name = metadata["bucket_name"]
        vm_image = metadata["vm_image"]
        service_account_name = metadata["service_account_name"]
        machine_type = MachineType(instance.machine_type.split("/")[-1])
        computing_resources = MACHINE_TYPE_TO_RESOURCE_MAP[machine_type]
        gpu_accelerator_type = (
            instance.guest_accelerators[0].accelerator_type
            if instance.guest_accelerators
            else None
        )
        zone = instance.zone.split("/")[-1]
        region = zone.rsplit("-", 1)[0]
        name = instance.name
        brand_name = metadata.get("brand_name")
        workflow_in_progress = next(
            filter(
                lambda workflow: workflow.workbench_id == name,
                workflows_in_progress,
            ),
            None,
        )
        status = (
            WORKBENCH_ACTIVITY_TYPE_MAP[workflow_in_progress.build_type]
            if workflow_in_progress
            else GCE_STATUS_MAP[instance.status]
        )
        workbench_type = WorkbenchType(metadata.get("type"))
        # Assume a single disk atteched to the instance.
        disk_size = instance.disks[0].disk_size_gb
        sharing_bucket_identifiers_metadata = metadata.get("sharing_bucket_identifiers")
        sharing_bucket_identifiers = (
            sharing_bucket_identifiers_metadata.split(",")
            if sharing_bucket_identifiers_metadata
            else []
        )
        return cls(
            id=name,
            resource_id=instance.id,
            dataset_identifier=dataset_identifier,
            bucket_name=bucket_name,
            vm_image=vm_image,
            region=Region(region),
            status=status,
            cpu=computing_resources.cpu,
            memory=computing_resources.memory,
            machine_type=machine_type,
            url=maybe_proxy_url,
            zone=zone,
            type=workbench_type,
            disk_size=disk_size,
            brand_name=brand_name,
            gpu_accelerator_type=gpu_accelerator_type,
            service_account_name=service_account_name,
            sharing_bucket_identifiers=sharing_bucket_identifiers,
        )


@dataclass
class BaseWorkbenchEntity:
    workbench_type: str
    workspace_project_id: str
    user_email: str


@dataclass
class WorkbenchCreate(BaseWorkbenchEntity):
    workspace_numeric_id: str
    machine_type: MachineType
    disk_size: int
    dataset_identifier: str
    bucket_name: str
    region: Region
    gpu_accelerator_type: Optional[GpuAcceleratorType] = None
    sharing_bucket_identifiers: List[str] = field(default_factory=list)
    vm_image: str = field(init=False)
    rstudio_image_url: str = field(init=False)

    def __post_init__(self):
        self.rstudio_image_url = app.config.rstudio_image_url
        self.vm_image = (
            "common-cu110-notebooks"
            if self.gpu_accelerator_type
            else "r-4-2-cpu-experimental-notebooks"
        )


@dataclass
class WorkbenchDestroy(BaseWorkbenchEntity):
    workbench_resource_id: str


@dataclass
class WorkbenchUpdate(BaseWorkbenchEntity):
    machine_type: MachineType
    workbench_resource_id: str


@dataclass
class WorkbenchToggleState:
    workbench_type: str
    workspace_project_id: str
    workbench_resource_id: str
    user_email: str
