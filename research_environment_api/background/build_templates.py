CREATE_JUPYTER_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "notebookcreation/python3.py",
            "${_NAME}",
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
            "TF_VAR_status=RUNNING",
            "TF_VAR_region=${_REGION}",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_bucket_name=${_BUCKET_NAME}",
            "TF_VAR_persistent_disk=${_DISK_SIZE}",
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

CREATE_WORKSPACE_STEPS = [
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

DESTROY_WORKSPACE_STEPS = [
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
        "args": ["-chdir=./vpc-sp", "destroy", "-auto-approve"],
        "env": [
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_perimeter_name=${_PERIMETER_NAME}",
        ],
    },
    {
        "name": "python",
        "args": ["python3", "project/python3.py", "${_PROJECT_ID}"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./project", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./project", "destroy", "-auto-approve"],
        "env": [
            "TF_VAR_billing_account=${_BILLING_ACCOUNT}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_app_eng_location=${_APPENGINE_REGION}",
            "TF_VAR_workspace_controller_project_name=${_WORKSPACE_CONTROLLER_PROJECT_NAME}",
        ],
    },
]


UPDATE_JUPYTER_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "notebookcreation/python3.py",
            "${_INSTANCE_NAME}",
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
        "args": ["-chdir=./notebookcreation", "apply", "-auto-approve"],
        "env": [
            "TF_VAR_machine_type=${_MACHINE_TYPE}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_dataset=${_DATASET}",
            "TF_VAR_region=${_REGION}",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_bucket_name=${_BUCKET_NAME}",
            "TF_VAR_vm_image=${_VM_IMAGE}",
            "TF_VAR_persistent_disk=${_DISK_SIZE}",
            "TF_VAR_gpu_accelerator=${_GPU_ACCELERATOR}",
            "TF_VAR_zone=${_ZONE}",
            "TF_VAR_jupyter_startup_script_bucket=${_JUPYTER_STARTUP_SCRIPT_BUCKET}",
        ],
    },
]

DESTROY_JUPYTER_WORKBENCH_STEPS = [
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
        "name": "hashicorp/terraform",
        "args": ["-chdir=./notebookcreation", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./notebookcreation", "destroy", "-auto-approve"],
        "env": [
            "TF_VAR_machine_type=${_MACHINE_TYPE}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_dataset=${_DATASET}",
            "TF_VAR_region=${_REGION}",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_bucket_name=${_BUCKET_NAME}",
            "TF_VAR_vm_image=${_VM_IMAGE}",
            "TF_VAR_gpu_accelerator=${_GPU_ACCELERATOR}",
            "TF_VAR_persistent_disk=${_DISK_SIZE}",
            "TF_VAR_zone=${_ZONE}",
            "TF_VAR_jupyter_startup_script_bucket=${_JUPYTER_STARTUP_SCRIPT_BUCKET}",
        ],
    },
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "compute",
            "disks",
            "delete",
            "${_NAME}-data",
            "--project=${_PROJECT_ID}",
            "--zone=${_ZONE}",
        ],
    },
]
