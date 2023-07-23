import random
import string

from google.cloud.devtools import cloudbuild_v1

from research_environment_api.background import build_templates
from research_environment_api.modules.app import app


def _base_build() -> cloudbuild_v1.Build:
    cloud_build = cloudbuild_v1.Build()
    cloud_build.service_account = app.config.cloud_build_service_account
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
    user_project_id: str,
    region: str,
    zone: str,
    machine_type: str,
    persistent_disk: int,
    gpu_accelerator_type: str,
    dataset_identifier: str,
    user_email: str,
    bucket_name: str,
    vm_image: str,
    jupyter_startup_script_bucket: str,
) -> cloudbuild_v1.Build:
    vm_image = (
        "common-cu110-notebooks"
        if gpu_accelerator_type
        else "r-4-2-cpu-experimental-notebooks"
    )
    instance_name = random.choice(string.ascii_letters)

    cloud_build = _base_build()
    cloud_build.steps = build_templates.CREATE_JUPYTER_WORKBENCH_STEPS
    cloud_build.substitutions = {
        "_PROJECT_ID": user_project_id,
        "_REGION": region,
        "_ZONE": zone,
        "_MACHINE_TYPE": machine_type,
        "_PERSISTENT_DISK": persistent_disk,
        "_GPU_ACCELERATOR": gpu_accelerator_type,
        "_DATASET": dataset_identifier,
        "_EMAIL_ID": user_email,
        "_BUCKET_NAME": bucket_name,
        "_VM_IMAGE": vm_image,
        "_JUPYTER_STARTUP_SCRIPT_BUCKET": jupyter_startup_script_bucket,
        "_NAME": instance_name,
    }

    return cloud_build
