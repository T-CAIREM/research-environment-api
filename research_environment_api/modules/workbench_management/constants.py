from research_environment_api.modules.workbench_management.handlers import jupyter_failure_handler
HANDLERS_MAPPING = {
    "jupyter_creation": jupyter_failure_handler
}


CLOUD_BUILD_TEMPLATES = {
    "CREATE_JUPYTER": [
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
    ],
    "DESTROY_JUPYTER": None,
}
