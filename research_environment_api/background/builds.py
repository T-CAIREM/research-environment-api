import random
import string
from typing import Optional

from google.cloud.devtools import cloudbuild_v1

from research_environment_api.background import build_templates
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.entities import (
    GpuAcceleratorType,
    MachineType,
    Region,
)


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
    gpu_accelerator_type: Optional[GpuAcceleratorType],
    dataset_identifier: str,
    user_email: str,
    bucket_name: str,
    vm_image: str,
    jupyter_startup_script_bucket: str,
) -> cloudbuild_v1.Build:
    instance_name = "-".join(
        [
            "jupyter",
            dataset_identifier,
            "".join(random.choices(string.ascii_lowercase, k=5)),
        ]
    )

    service_account_name = "-".join(
        [
            "jupyter",
            dataset_identifier[:15],
            "".join(random.choices(string.ascii_lowercase, k=5)),
        ]
    )

    cloud_build = _base_build()
    cloud_build.steps = build_templates.CREATE_JUPYTER_WORKBENCH_STEPS
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
        "_JUPYTER_STARTUP_SCRIPT_BUCKET": jupyter_startup_script_bucket,
        "_INSTANCE_NAME": instance_name,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
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
    jupyter_startup_script_bucket: str,
    workbench_name: str,
    service_account_name: str,
) -> cloudbuild_v1.Build:
    cloud_build = _base_build()
    cloud_build.steps = build_templates.UPDATE_JUPYTER_WORKBENCH_STEPS
    cloud_build.substitutions = {
        "_MACHINE_TYPE": machine_type.value,
        "_PROJECT_ID": workspace_project_id,
        "_INSTANCE_NAME": workbench_name,
        "_REGION": region.value,
        "_DATASET": dataset_identifier,
        "_EMAIL_ID": user_email,
        "_BUCKET_NAME": bucket_name,
        "_VM_IMAGE": vm_image,
        "_DISK_SIZE": str(disk_size),
        "_GPU_ACCELERATOR": _normalize_gpu_accelerator_type(gpu_accelerator_type),
        "_ZONE": zone,
        "_JUPYTER_STARTUP_SCRIPT_BUCKET": jupyter_startup_script_bucket,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
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
    jupyter_startup_script_bucket: str,
    workbench_name: str,
    service_account_name: str,
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
        "_GPU_ACCELERATOR": _normalize_gpu_accelerator_type(gpu_accelerator_type),
        "_VM_IMAGE": vm_image,
        "_INSTANCE_NAME": workbench_name,
        "_ZONE": zone,
        "_JUPYTER_STARTUP_SCRIPT_BUCKET": jupyter_startup_script_bucket,
        "_SERVICE_ACCOUNT_NAME": service_account_name,
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
        "_APPENGINE_REGION": region.value,
        "_WORKSPACE_CONTROLLER_PROJECT_NAME": app.config.project_id,
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
        "_APPENGINE_REGION": region.value,
        "_WORKSPACE_CONTROLLER_PROJECT_NAME": app.config.project_id,
        "_PERIMETER_NAME": app.config.vpc_secure_perimeter_name,
    }

    return cloud_build


def _normalize_gpu_accelerator_type(
    gpu_accelerator_type: Optional[GpuAcceleratorType],
) -> str:
    return "" if not gpu_accelerator_type else gpu_accelerator_type.value
