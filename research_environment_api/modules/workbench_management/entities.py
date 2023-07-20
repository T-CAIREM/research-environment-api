from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional, Self

from google.cloud.appengine_admin_v1.types.service import Service as AppEngineService
from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.constants import (
    MACHINE_TYPE_TO_RESOURCE_MAP,
)


class WorkbenchType(StrEnum):
    JUPYTER = "jupyter"
    RSTUDIO = "rstudio"


@dataclass
class Workbench:
    gcp_identifier: str
    resource_status: str
    dataset_identifier: str
    cpu: float
    memory: float
    type: WorkbenchType
    url: Optional[str]

    @classmethod
    def from_gce_instance(cls, instance: ComputeEngineInstance):
        maybe_proxy_url: Optional[str] = next(
            (
                metadata.value
                for metadata in instance.metadata.items
                if metadata.key == "proxy-url"
            ),
            None,
        )
        machine_type = instance.machine_type.split("/")[-1]
        computing_resources = MACHINE_TYPE_TO_RESOURCE_MAP[machine_type]
        return cls(
            gcp_identifier=str(instance.id),
            dataset_identifier=instance.labels["dataset_identifier"],
            resource_status=instance.status,
            cpu=computing_resources.cpu,
            memory=computing_resources.memory,
            url=maybe_proxy_url,
            type=WorkbenchType.JUPYTER,
        )

    @classmethod
    def from_app_engine_service_and_version(
        cls, service: AppEngineService, version: AppEngineVersion
    ):
        return cls(
            gcp_identifier=version.id,
            dataset_identifier=service.labels["dataset_identifier"],
            resource_status=version.serving_status,
            cpu=version.resources.cpu,
            memory=version.resources.memory_gb,
            url=version.version_url,
            type=WorkbenchType.RSTUDIO,
        )


@dataclass
class JupyterWorkbench:
    machine_type: str
    user_project_id: str
    dataset: str
    email_id: str
    bucket_name: str
    region: str
    persistent_disk: str
    vm_image: str
    gpu_accelerator: str
    jupyter_startup_script_bucket: str = field(init=False)

    def __post_init__(self):
        self.jupyter_startup_script_bucket = app.config.jupyter_startup_script
        self.persistent_disk = str(self.persistent_disk)


@dataclass
class JupyterWorkbenchStop:
    user_project: str
    instance_name: str
    gcp_identifier: str
