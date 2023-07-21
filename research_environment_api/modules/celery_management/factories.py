import random
import string

from google.cloud.devtools import cloudbuild_v1


class BuildFactory:
    def __init__(self, project_id: str, build_source: dict):
        self.build = cloudbuild_v1.Build()
        self.build.service_account = f"projects/{project_id}/serviceAccounts/workspace-manager@{project_id}.iam.gserviceaccount.com"
        self.build.options = {"logging": "CLOUD_LOGGING_ONLY"}
        self.build.source = build_source

    @staticmethod
    def _generate_jupyter_name():
        return random.choice(string.ascii_letters)

    def create_jupyter(
        self,
        machine_type: str,
        user_project_id: str,
        dataset: str,
        email_id: str,
        bucket_name: str,
        region: str,
        persistent_disk: int,
        gpu_accelerator: str,
        vm_image: str,
        zone: str,
        jupyter_startup_script_bucket: str,
    ):
        build = self.build
        build.steps = [
            {
                "name": "python",
                "args": [
                    "python3",
                    "notebookcreation/python3.py",
                    "${_PROJECT_ID}",
                    "workspace-${_DATASET}-jupyterlab",
                ],
            },
            {
                "name": "python",
                "args": ["python3", "notebookcreation/python4.py", "${_BUCKET_NAME}"],
            },
            {
                "name": "hashicorp/terraform",
                "args": ["-chdir=./notebookcreation", "init", "-reconfigure"],
            },
            {
                "name": "hashicorp/terraform",
                "args": ["-chdir=./notebookcreation", "plan", "-out=tfplan.out"],
                "env": [
                    "TF_VAR_machine_type=${_MACHINE_TYPE}",
                    "TF_VAR_project_id=${_PROJECT_ID}",
                    "TF_VAR_dataset=${_DATASET}",
                    "TF_VAR_status=${_STATUS}",
                    "TF_VAR_region=${_REGION}",
                    "TF_VAR_emailid=${_EMAIL_ID}",
                    "TF_VAR_bucket_name=${_BUCKET_NAME}",
                    "TF_VAR_persistent_disk=${_PERSISTENT_DISK}",
                    "TF_VAR_gpu_accelerator=${_GPU_ACCELERATOR}",
                    "TF_VAR_vm_image=${_VM_IMAGE}",
                    "TF_VAR_zone=${_ZONE}",
                    "TF_VAR_jupyter_startup_script_bucket=${_JUPYTER_STARTUP_SCRIPT_BUCKET}",
                    "TF_VAR_name=${_NAME}",
                ],
            },
            {
                "name": "hashicorp/terraform",
                "entrypoint": "/bin/sh",
                "allow_failure": True,
                "args": [
                    "-c",
                    "terraform -chdir=./notebookcreation apply -auto-approve tfplan.out &> output.txt",
                ],
            },
            {
                "name": "python",
                "args": ["python3", "notebookcreation/check_errors.py"],
            },
        ]

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
            "_NAME": self._generate_jupyter_name(),
        }

        return build

    def create_workspace(
        self,
        billing_account: str,
        user_project_id: str,
        email_id: str,
        region: str,
        perimeter_name: str,
        appengine_region: str,
        controller_project_name: str,
    ):
        build = self.build
        build.steps = [
            {
                "name": "python",
                "args": ["python3", "project/python3.py", "${_PROJECT_ID}"],
                "wait_for": ["-"],
            },
            {
                "name": "hashicorp/terraform",
                "args": ["-chdir=./project", "init", "-reconfigure"],
            },
            {
                "name": "hashicorp/terraform",
                "args": ["-chdir=./project", "apply", "-auto-approve"],
                "env": [
                    "TF_VAR_billing_account=${_BILLING_ACCOUNT}",
                    "TF_VAR_project_id=${_PROJECT_ID}",
                    "TF_VAR_emailid=${_EMAIL_ID}",
                    "TF_VAR_app_eng_location=${_APPENGINE_REGION}",
                    "TF_VAR_workspace_controller_project_name=${_WORKSPACE_CONTROLLER_PROJECT_NAME}",
                ],
            },
            {
                "name": "python",
                "args": [
                    "python3",
                    "appengine-rstudio/python3.py",
                    "default",
                    "${_SERVICE_ACCOUNT}",
                    "${_MACHINE_TYPE}",
                    "${_REGION}",
                ],
                "wait_for": ["-"],
            },
            {
                "name": "gcr.io/cloud-builders/gcloud",
                "args": [
                    "app",
                    "deploy",
                    "std-appengine/app.yaml",
                    "--project=${_PROJECT_ID}",
                ],
            },
            {
                "name": "python",
                "args": ["python3", "vpc-sp/python3.py", "${_PROJECT_ID}"],
                "wait_for": ["-"],
            },
            {
                "name": "hashicorp/terraform",
                "args": ["-chdir=./vpc-sp", "init", "-reconfigure"],
            },
            {
                "name": "hashicorp/terraform",
                "args": ["-chdir=./vpc-sp", "apply", "-auto-approve"],
                "env": [
                    "TF_VAR_project_id=${_PROJECT_ID}",
                    "TF_VAR_perimeter_name=${_PERIMETER_NAME}",
                ],
            },
        ]
        build.substitutions = {
            "_BILLING_ACCOUNT": billing_account,
            "_PROJECT_ID": user_project_id,
            "_EMAIL_ID": email_id,
            "_MACHINE_TYPE": "n1-standard-1",
            "_REGION": region,
            "_SERVICE_ACCOUNT": f"default-rstudio@{user_project_id}.iam.gserviceaccount.com",
            "_APPENGINE_REGION": appengine_region,
            "_WORKSPACE_CONTROLLER_PROJECT_NAME": controller_project_name,
            "_PERIMETER_NAME": perimeter_name,
        }

        return build
