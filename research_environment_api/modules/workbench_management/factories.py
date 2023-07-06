from google.cloud.devtools import cloudbuild_v1
from research_environment_api.modules.workbench_management.constants import (
    CLOUD_BUILD_TEMPLATES,
)


class BuildFactory:
    def __init__(self, project_id: str, build_source: dict):
        self.build = cloudbuild_v1.Build()
        self.build.service_account = f"projects/{project_id}/serviceAccounts/workspace-creator@{project_id}.iam.gserviceaccount.com"
        self.build.options = {"logging": "CLOUD_LOGGING_ONLY"}
        self.build.source = build_source

    def create_jupyter(
        self,
        machine_type: str,
        user_project_id: str,
        dataset: str,
        email_id: str,
        bucket_name: str,
        region: str,
        persistent_disk: str,
        gpu_accelerator: str,
        vm_image: str,
        zone: str,
        jupyter_startup_script_bucket: str,
    ):
        build = self.build
        build.steps = CLOUD_BUILD_TEMPLATES["CREATE_JUPYTER"]
        build.substitutions = {
            "_MACHINE_TYPE": machine_type,
            "_PROJECT_ID": user_project_id,
            "_DATASET": dataset,
            "_STATUS": "RUNNING",
            "_REGION": region,
            "_EMAIL_ID": email_id,
            "_BUCKET_NAME": bucket_name,
            "_PERSISTENT_DISK": persistent_disk,
            "_GPU_ACCELERATOR": gpu_accelerator,
            "_VM_IMAGE": vm_image,
            "_ZONE": zone,
            "_JUPYTER_STARTUP_SCRIPT_BUCKET": jupyter_startup_script_bucket,
        }

        return build
