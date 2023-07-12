from google.cloud.devtools import cloudbuild_v1


class BuildFactory:
    def __init__(self, project_id: str, build_source: dict):
        self.build = cloudbuild_v1.Build()
        self.build.service_account = f"projects/{project_id}/serviceAccounts/workspace-manager@{project_id}.iam.gserviceaccount.com"
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
        }

        return build
