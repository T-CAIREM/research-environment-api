from typing import Optional, List

from google.cloud.devtools import cloudbuild_v1

from research_environment_api.background import build_templates
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.entities import (
    GpuAcceleratorType,
    MachineType,
    Region,
    WorkbenchType,
)


GPU_ACCELERATOR_TYPE_TO_NAME_MAP = {
    GpuAcceleratorType.TESLA_T4: "NVIDIA_TESLA_T4",
    None: "",
}


def _base_build() -> cloudbuild_v1.Build:
    cloud_build = cloudbuild_v1.Build()
    cloud_build.service_account = app.config.cloud_build_service_account_name
    cloud_build.options = {"logging": "CLOUD_LOGGING_ONLY"}
    cloud_build.source = {
        "repo_source": {
            "project_id": app.config.project_id,
            "repo_name": app.config.terraform_repo_name,
            "branch_name": app.config.terraform_branch_name,
        }
    }
    return cloud_build


def create_jupyter_workbench_build(
    workspace_project_id: str,
    region: Region,
    zone: str,
    machine_type: MachineType,
    disk_size: int,
    instance_name: str,
    service_account_name: str,
    gpu_accelerator_type: Optional[GpuAcceleratorType],
    dataset_identifier: str,
    user_email: str,
    bucket_name: str,
    vm_image: str,
    sharing_bucket_permission_dict: dict[str, str],
) -> cloudbuild_v1.Build:
    cloud_build = _base_build()
    cloud_build.steps = build_templates.CREATE_JUPYTER_WORKBENCH_STEPS
    cloud_build.substitutions = {
        "_PROJECT_ID": workspace_project_id,
        "_REGION": region.value,
        "_ZONE": zone,
        "_MACHINE_TYPE": machine_type.value,
        "_DISK_SIZE": str(disk_size),
        "_GPU_ACCELERATOR": GPU_ACCELERATOR_TYPE_TO_NAME_MAP[gpu_accelerator_type],
        "_DATASET": dataset_identifier,
        "_EMAIL_ID": user_email,
        "_BUCKET_NAME": bucket_name,
        "_VM_IMAGE": vm_image,
        "_JUPYTER_STARTUP_SCRIPT_BUCKET": app.config.jupyter_startup_script,
        "_INSTANCE_NAME": instance_name,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
        "_WORKBENCH_TYPE": WorkbenchType.JUPYTER,
        "_SHARING_BUCKET_IDENTIFIERS": ",".join(sharing_bucket_permission_dict.keys()),
        "_SHARING_BUCKET_PERMISSIONS": ",".join(
            sharing_bucket_permission_dict.values()
        ),
    }

    return cloud_build


def update_jupyter_workbench_build(
    workspace_project_id: str,
    region: Region,
    zone: str,
    machine_type: MachineType,
    disk_size: int,
    gpu_accelerator_type: Optional[GpuAcceleratorType],
    dataset_identifier: str,
    user_email: str,
    bucket_name: str,
    vm_image: str,
    instance_name: str,
    service_account_name: str,
    sharing_bucket_permission_dict: dict[str, str],
) -> cloudbuild_v1.Build:
    cloud_build = _base_build()
    cloud_build.steps = build_templates.UPDATE_JUPYTER_WORKBENCH_STEPS
    cloud_build.substitutions = {
        "_MACHINE_TYPE": machine_type.value,
        "_PROJECT_ID": workspace_project_id,
        "_INSTANCE_NAME": instance_name,
        "_REGION": region.value,
        "_DATASET": dataset_identifier,
        "_EMAIL_ID": user_email,
        "_BUCKET_NAME": bucket_name,
        "_VM_IMAGE": vm_image,
        "_DISK_SIZE": str(disk_size),
        "_GPU_ACCELERATOR": GPU_ACCELERATOR_TYPE_TO_NAME_MAP[gpu_accelerator_type],
        "_ZONE": zone,
        "_JUPYTER_STARTUP_SCRIPT_BUCKET": app.config.jupyter_startup_script,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
        "_WORKBENCH_TYPE": WorkbenchType.JUPYTER,
        "_SHARING_BUCKET_IDENTIFIERS": ",".join(sharing_bucket_permission_dict.keys()),
        "_SHARING_BUCKET_PERMISSIONS": ",".join(
            sharing_bucket_permission_dict.values()
        ),
    }

    return cloud_build


def destroy_jupyter_workbench_build(
    workspace_project_id: str,
    region: Region,
    zone: str,
    machine_type: MachineType,
    disk_size: int,
    gpu_accelerator_type: Optional[GpuAcceleratorType],
    dataset_identifier: str,
    user_email: str,
    bucket_name: str,
    vm_image: str,
    instance_name: str,
    service_account_name: str,
    sharing_bucket_identifiers: list[str],
) -> cloudbuild_v1.Build:
    cloud_build = _base_build()
    cloud_build.steps = build_templates.DESTROY_JUPYTER_WORKBENCH_STEPS
    cloud_build.substitutions = {
        "_MACHINE_TYPE": machine_type.value,
        "_PROJECT_ID": workspace_project_id,
        "_REGION": region.value,
        "_DATASET": dataset_identifier,
        "_EMAIL_ID": user_email,
        "_BUCKET_NAME": bucket_name,
        "_DISK_SIZE": str(disk_size),
        "_GPU_ACCELERATOR": GPU_ACCELERATOR_TYPE_TO_NAME_MAP[gpu_accelerator_type],
        "_VM_IMAGE": vm_image,
        "_INSTANCE_NAME": instance_name,
        "_ZONE": zone,
        "_JUPYTER_STARTUP_SCRIPT_BUCKET": app.config.jupyter_startup_script,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
        "_WORKBENCH_TYPE": WorkbenchType.JUPYTER,
        "_SHARING_BUCKET_IDENTIFIERS": ",".join(sharing_bucket_identifiers),
    }

    return cloud_build


def create_workspace_build(
    billing_account_id: str,
    workspace_project_id: str,
    user_email: str,
    region: Region,
):
    cloud_build = _base_build()
    cloud_build.steps = build_templates.CREATE_WORKSPACE_STEPS
    cloud_build.substitutions = {
        "_BILLING_ACCOUNT": billing_account_id,
        "_PROJECT_ID": workspace_project_id,
        "_EMAIL_ID": user_email,
        "_WORKSPACE_CONTROLLER_PROJECT_NAME": app.config.project_id,
        "_PERIMETER_NAME": app.config.vpc_secure_perimeter_name,
    }

    return cloud_build


def create_shared_workspace_build(
    billing_account_id: str,
    workspace_project_id: str,
    user_email: str,
):
    cloud_build = _base_build()
    cloud_build.steps = build_templates.CREATE_SHARED_WORKSPACE_STEPS
    cloud_build.substitutions = {
        "_BILLING_ACCOUNT": billing_account_id,
        "_PROJECT_ID": workspace_project_id,
        "_EMAIL_ID": user_email,
        "_SHARING_FOLDER_ID": app.config.sharing_folder_id,
        "_PERIMETER_NAME": app.config.vpc_secure_perimeter_name,
    }

    return cloud_build


def destroy_workspace_build(
    billing_account_id: str, workspace_project_id: str, user_email: str, region: Region
):
    cloud_build = _base_build()
    cloud_build.steps = build_templates.DESTROY_WORKSPACE_STEPS
    cloud_build.substitutions = {
        "_BILLING_ACCOUNT": billing_account_id,
        "_PROJECT_ID": workspace_project_id,
        "_EMAIL_ID": user_email,
        "_WORKSPACE_CONTROLLER_PROJECT_NAME": app.config.project_id,
        "_PERIMETER_NAME": app.config.vpc_secure_perimeter_name,
    }

    return cloud_build


def destroy_shared_workspace_build(
    billing_account_id: str,
    workspace_project_id: str,
    user_email: str,
):
    cloud_build = _base_build()
    cloud_build.steps = build_templates.DESTROY_SHARED_WORKSPACE_STEPS
    cloud_build.substitutions = {
        "_BILLING_ACCOUNT": billing_account_id,
        "_PROJECT_ID": workspace_project_id,
        "_EMAIL_ID": user_email,
        "_SHARING_FOLDER_ID": app.config.sharing_folder_id,
        "_PERIMETER_NAME": app.config.vpc_secure_perimeter_name,
    }

    return cloud_build


def _normalize_gpu_accelerator_type(
    gpu_accelerator_type: Optional[GpuAcceleratorType],
) -> str:
    return "" if not gpu_accelerator_type else gpu_accelerator_type.value


def create_rstudio_workbench_build(
    workspace_project_id: str,
    workspace_numeric_id: str,
    region: Region,
    zone: str,
    machine_type: MachineType,
    disk_size: int,
    instance_name: str,
    service_account_name: str,
    gpu_accelerator_type: Optional[GpuAcceleratorType],
    dataset_identifier: str,
    user_email: str,
    bucket_name: str,
    sharing_bucket_permission_dict: dict[str, str],
) -> cloudbuild_v1.Build:
    cloud_build = _base_build()
    cloud_build.steps = build_templates.CREATE_RSTUDIO_WORKBENCH_STEPS
    cloud_build.substitutions = {
        "_PROJECT_ID": workspace_project_id,
        "_REGION": region.value,
        "_ZONE": zone,
        "_MACHINE_TYPE": machine_type.value,
        "_DISK_SIZE": str(disk_size),
        "_GPU_ACCELERATOR": _normalize_gpu_accelerator_type(gpu_accelerator_type),
        "_DATASET": dataset_identifier,
        "_EMAIL_ID": user_email,
        "_BUCKET_NAME": bucket_name,
        "_VM_IMAGE": app.config.rstudio_image_url,
        "_BRAND_NAME": f"projects/{workspace_numeric_id}/brands/{workspace_numeric_id}",
        "_RSTUDIO_STARTUP_SCRIPT_BUCKET": app.config.rstudio_startup_script,
        "_INSTANCE_NAME": instance_name,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
        "_NETWORK_NAME": app.config.network_name,
        "_RSTUDIO_DNS_PROJECT": app.config.rstudio_dns_project,
        "_RSTUDIO_DNS_ZONE": app.config.rstudio_dns_zone,
        "_RSTUDIO_DOMAIN_NAME": app.config.rstudio_domain_name,
        "_RSTUDIO_SSL_PRIVATE_KEY": app.config.rstudio_ssl_private_key,
        "_RSTUDIO_SSL_CERTIFICATE": app.config.rstudio_ssl_certificate,
        "_WORKBENCH_TYPE": WorkbenchType.RSTUDIO,
        "_SHARING_BUCKET_IDENTIFIERS": ",".join(sharing_bucket_permission_dict.keys()),
        "_SHARING_BUCKET_PERMISSIONS": ",".join(
            sharing_bucket_permission_dict.values()
        ),
    }

    return cloud_build


def update_rstudio_workbench_build(
    workspace_project_id: str,
    region: Region,
    zone: str,
    machine_type: MachineType,
    disk_size: int,
    instance_name: str,
    service_account_name: str,
    gpu_accelerator_type: Optional[GpuAcceleratorType],
    dataset_identifier: str,
    user_email: str,
    bucket_name: str,
    vm_image: str,
    brand_name: str,
    sharing_bucket_permission_dict: dict[str, str],
) -> cloudbuild_v1.Build:
    cloud_build = _base_build()
    cloud_build.steps = build_templates.UPDATE_RSTUDIO_WORKBENCH_STEPS
    cloud_build.substitutions = {
        "_PROJECT_ID": workspace_project_id,
        "_REGION": region.value,
        "_ZONE": zone,
        "_MACHINE_TYPE": machine_type.value,
        "_DISK_SIZE": str(disk_size),
        "_GPU_ACCELERATOR": _normalize_gpu_accelerator_type(gpu_accelerator_type),
        "_DATASET": dataset_identifier,
        "_EMAIL_ID": user_email,
        "_BUCKET_NAME": bucket_name,
        "_VM_IMAGE": vm_image,
        "_BRAND_NAME": brand_name,
        "_RSTUDIO_STARTUP_SCRIPT_BUCKET": app.config.rstudio_startup_script,
        "_INSTANCE_NAME": instance_name,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
        "_NETWORK_NAME": app.config.network_name,
        "_RSTUDIO_DNS_PROJECT": app.config.rstudio_dns_project,
        "_RSTUDIO_DNS_ZONE": app.config.rstudio_dns_zone,
        "_RSTUDIO_DOMAIN_NAME": app.config.rstudio_domain_name,
        "_RSTUDIO_SSL_PRIVATE_KEY": app.config.rstudio_ssl_private_key,
        "_RSTUDIO_SSL_CERTIFICATE": app.config.rstudio_ssl_certificate,
        "_WORKBENCH_TYPE": WorkbenchType.RSTUDIO,
        "_SHARING_BUCKET_IDENTIFIERS": ",".join(sharing_bucket_permission_dict.keys()),
        "_SHARING_BUCKET_PERMISSIONS": ",".join(
            sharing_bucket_permission_dict.values()
        ),
    }

    return cloud_build


def destroy_rstudio_workbench_build(
    workspace_project_id: str,
    region: Region,
    zone: str,
    machine_type: MachineType,
    disk_size: int,
    instance_name: str,
    service_account_name: str,
    gpu_accelerator_type: Optional[GpuAcceleratorType],
    dataset_identifier: str,
    user_email: str,
    bucket_name: str,
    vm_image: str,
    brand_name: str,
    sharing_bucket_identifiers: list[str],
) -> cloudbuild_v1.Build:
    cloud_build = _base_build()
    cloud_build.steps = build_templates.DESTROY_RSTUDIO_WORKBENCH_STEPS
    cloud_build.substitutions = {
        "_PROJECT_ID": workspace_project_id,
        "_REGION": region.value,
        "_ZONE": zone,
        "_MACHINE_TYPE": machine_type.value,
        "_DISK_SIZE": str(disk_size),
        "_GPU_ACCELERATOR": _normalize_gpu_accelerator_type(gpu_accelerator_type),
        "_DATASET": dataset_identifier,
        "_EMAIL_ID": user_email,
        "_BUCKET_NAME": bucket_name,
        "_VM_IMAGE": vm_image,
        "_BRAND_NAME": brand_name,
        "_RSTUDIO_STARTUP_SCRIPT_BUCKET": app.config.rstudio_startup_script,
        "_INSTANCE_NAME": instance_name,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
        "_NETWORK_NAME": app.config.network_name,
        "_RSTUDIO_DNS_PROJECT": app.config.rstudio_dns_project,
        "_RSTUDIO_DNS_ZONE": app.config.rstudio_dns_zone,
        "_RSTUDIO_DOMAIN_NAME": app.config.rstudio_domain_name,
        "_RSTUDIO_SSL_PRIVATE_KEY": app.config.rstudio_ssl_private_key,
        "_RSTUDIO_SSL_CERTIFICATE": app.config.rstudio_ssl_certificate,
        "_WORKBENCH_TYPE": WorkbenchType.RSTUDIO,
        "_SHARING_BUCKET_IDENTIFIERS": ",".join(sharing_bucket_identifiers),
    }

    return cloud_build
