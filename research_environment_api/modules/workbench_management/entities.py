import random
import string
from collections import namedtuple
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable, Optional, Union

from google.cloud.appengine_admin_v1.types.service import Service as AppEngineService
from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.background.enums import BuildType
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import models

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


class WorkspaceStatus(StrEnum):
    CREATED = "created"
    CREATING = "creating"
    DESTROYING = "destroying"


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

WORKSPACE_ACTIVITY_TYPE_MAP = {
    BuildType.WORKSPACE_CREATION: WorkspaceStatus.CREATING,
    BuildType.WORKSPACE_DELETION: WorkspaceStatus.DESTROYING,
}

RSTUDIO_STATUS_MAP = {
    "SERVING": WorkbenchStatus.RUNNING,
    "STOPPED": WorkbenchStatus.STOPPED,
}

GOOGLE_REGIONS_SHORTCUTS = {
    Region.US_CENTRAL.value: "us-c1",
    Region.EUROPE_WEST.value: "eu-w3",
    Region.NORTHAMERICA_NORTHEAST.value: "na-ne3",
    Region.AUSTRALIA_SOUTHEAST.value: "au-se1",
}


@dataclass
class Workbench:
    gcp_identifier: str
    status: WorkbenchStatus
    dataset_identifier: str
    cpu: float
    memory: float
    disk_size: int
    type: WorkbenchType
    machine_type: MachineType
    region: Region
    name: str
    bucket_name: str
    vm_image: str
    service_account_name: str
    url: Optional[str] = None
    zone: Optional[str] = None
    gpu_accelerator_type: Optional[GpuAcceleratorType] = None

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
        instance_id = instance.name
        zone = instance.zone.split("/")[-1]
        region = zone.rsplit("-", 1)[0]
        workflow_in_progress = next(
            filter(
                lambda workflow: workflow.workbench_id == instance_id,
                workflows_in_progress,
            ),
            None,
        )
        status = (
            WORKBENCH_ACTIVITY_TYPE_MAP[workflow_in_progress.build_type]
            if workflow_in_progress
            else GCE_STATUS_MAP[instance.status]
        )
        # Assume a single disk atteched to the instance.
        disk_size = instance.disks[0].disk_size_gb
        return cls(
            gcp_identifier=instance_id,
            dataset_identifier=dataset_identifier,
            name=instance.name,
            bucket_name=bucket_name,
            vm_image=vm_image,
            region=Region(region),
            status=status,
            cpu=computing_resources.cpu,
            memory=computing_resources.memory,
            machine_type=machine_type,
            url=maybe_proxy_url,
            zone=zone,
            type=WorkbenchType.JUPYTER,
            disk_size=disk_size,
            gpu_accelerator_type=gpu_accelerator_type,
            service_account_name=service_account_name,
        )

    @classmethod
    def from_app_engine_service_and_version(
        cls,
        service: AppEngineService,
        version: AppEngineVersion,
        workflows_in_progress: Iterable[models.WorkbenchActivity],
    ):
        with app.database_session() as session:
            app_engine_metadata = (
                session.query(models.AppEngineMetadata)
                .filter_by(instance_id=service.id)
                .one()
            )
            service_account = next(iter(version.service_account.split("@")))
            url = (version.version_url).replace(f"{version.id}-dot-", "")
            workflow_in_progress = next(
                filter(
                    lambda workflow: workflow.workbench_id == version.id,
                    workflows_in_progress,
                ),
                None,
            )
            status = (
                WORKBENCH_ACTIVITY_TYPE_MAP[workflow_in_progress.build_type]
                if workflow_in_progress
                else RSTUDIO_STATUS_MAP[version.serving_status.name]
            )

            return cls(
                gcp_identifier=version.id,
                dataset_identifier=app_engine_metadata.dataset_identifier,
                status=status,
                cpu=version.resources.cpu,
                memory=version.resources.memory_gb,
                url=url,
                type=WorkbenchType.RSTUDIO,
                service_account_name=service_account,
                bucket_name=app_engine_metadata.bucket_name,
                vm_image=app_engine_metadata.vm_image,
                region=Region(app_engine_metadata.region),
                name=service.id,
                disk_size=app_engine_metadata.disk_size,
                machine_type=MachineType(app_engine_metadata.machine_type),
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


@dataclass
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


@dataclass
class WorkspaceCreation:
    region: Region
    user_email: str
    workspace_project_id: str = field(init=False)
    billing_account_id: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.user_email.split("@")
        self.workspace_project_id = self._workspace_project_id()

    def _workspace_project_id(self):
        workspace_project_id = (
            f"{self.username[:15]}-{GOOGLE_REGIONS_SHORTCUTS[self.region.value]}-"
            + "".join(random.choices(string.ascii_lowercase, k=5))
        )
        return workspace_project_id


@dataclass
class WorkspaceDeletion:
    workspace_project_id: str
    region: Region
    user_email: str
    billing_account_id: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.user_email.split("@")


@dataclass
class WorkspaceListQuery:
    email: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.email.split("@")


@dataclass
class BillingInfo:
    billing_enabled: bool
    billing_account_id: str


@dataclass
class Workspace:
    gcp_project_id: str
    billing_info: BillingInfo
    region: str
    workbenches: Iterable[Workbench]
    status: WorkspaceStatus


@dataclass
class EntityScaffolding:
    id: str
    status: Union[WorkbenchStatus, WorkspaceStatus]
    gcp_project_id: str
