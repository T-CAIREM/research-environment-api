from typing import Self, Optional
from dataclasses import dataclass, field
from research_environment_api.modules.config import config

from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance
from google.cloud.appengine_admin_v1.types.version import Version as AppEngineVersion

from research_environment_api.modules.workbench_management.constants import (
    MACHINE_TYPE_TO_RESOURCE_MAP,
)
from research_environment_api.modules.workbench_management.models import (
    WorkbenchMetadata,
)


@dataclass
class GcpWorkbenchResource:
    id: str
    zone: str
    status: str
    cpu: float
    memory: float
    url: Optional[str]

    @classmethod
    def from_gce_instance(cls, instance: ComputeEngineInstance):
        maybe_proxy_url: Optional[str] = next(
            metadata.value
            for metadata in instance.metadata.items
            if metadata.key == "proxy-url"
        )
        machine_type = instance.machine_type.split("/")[-1]
        computing_resources = MACHINE_TYPE_TO_RESOURCE_MAP[machine_type]
        return cls(
            id=str(instance.id),
            zone=instance.zone,
            status=instance.status,
            cpu=computing_resources.cpu,
            memory=computing_resources.memory,
            url=maybe_proxy_url,
        )

    @classmethod
    def from_app_engine_version(cls, version: AppEngineVersion):
        return cls(
            id=version.id,
            zone=version.zones,
            status=version.serving_status,
            cpu=version.resources.cpu,
            memory=version.resources.memory_gb,
            url=version.version_url,
        )


@dataclass
class Workbench:
    gcp_identifier: str
    zone: str
    resource_status: str
    dataset_slug: str
    dataset_version: str
    cpu: float
    memory: float
    url: Optional[str]

    @classmethod
    def from_gcp_resource_and_metadata(
        cls, resource: GcpWorkbenchResource, metadata: WorkbenchMetadata
    ) -> Self:
        return cls(
            gcp_identifier=resource.id,
            zone=resource.zone,
            resource_status=resource.status,
            url=resource.url,
            cpu=resource.cpu,
            memory=resource.memory,
            dataset_slug=metadata.dataset_slug,
            dataset_version=metadata.dataset_version,
        )


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
        self.jupyter_startup_script_bucket = config.jupyter_startup_script
        self.persistent_disk = str(self.persistent_disk)
