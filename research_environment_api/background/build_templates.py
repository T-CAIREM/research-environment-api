CREATE_JUPYTER_WORKBENCH_STEPS = [
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
            "TF_VAR_name=${_INSTANCE_NAME}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT_NAME}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "entrypoint": "/bin/sh",
        "args": ["notebookcreation/terraform_apply.sh"],
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
        "args": [
            "python3",
            "appengine-rstudio/python3.py",
            "default",
            "${_SERVICE_ACCOUNT}",
            "n1-standard-1",
            "${_REGION}",
            "",
            "",
            "${_PROJECT_ID}",
        ],
        "wait_for": ["-"],
    },
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": ["app", "deploy", "std-appengine/app.yaml", "--project=${_PROJECT_ID}"],
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
            "TF_VAR_name=${_INSTANCE_NAME}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT_NAME}",
        ],
    },
]

DESTROY_JUPYTER_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "notebookcreation/python3.py",
            "${_INSTANCE_NAME}",
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
            "TF_VAR_name=${_INSTANCE_NAME}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT_NAME}",
        ],
    },
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "compute",
            "disks",
            "delete",
            "${_INSTANCE_NAME}-data",
            "--project=${_PROJECT_ID}",
            "--zone=${_ZONE}",
        ],
    },
]

STOP_RSTUDIO_WORKBENCH_STEPS = [
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "app",
            "versions",
            "stop",
            "${_VERSION_ID}",
            "--project=${_PROJECT_ID}",
            "-q",
        ],
    }
]

CREATE_RSTUDIO_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "vmcreation/python3.py",
            "${_INSTANCE_NAME}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vmcreation", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vmcreation", "apply", "-auto-approve"],
        "env": [
            "TF_VAR_name=${_INSTANCE_NAME}",
            "TF_VAR_machine_type=${_MACHINE_TYPE}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_dataset=${_DATASET}",
            "TF_VAR_status=RUNNING",
            "TF_VAR_region=${_REGION}",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_workspace_controller_project_name=${_WORKSPACE_CONTROLLER_PROJECT_NAME}",
            "TF_VAR_data_project_name=${_DATA_PROJECT_NAME}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT}",
        ],
    },
    {
        "name": "python",
        "args": [
            "python3",
            "appengine-rstudio/python3.py",
            "${_INSTANCE_NAME}",
            "${_SERVICE_ACCOUNT}",
            "${_MACHINE_TYPE}",
            "${_REGION}",
            "${_DISK_SIZE}",
            "${_BUCKET_NAME}",
            "${_PROJECT_ID}",
        ],
    },
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "app",
            "deploy",
            "appengine-rstudio/app.yaml",
            "--image-url=${_IMAGE_URL}",
            "--project=${_PROJECT_ID}",
            "--bucket=gs://rstudio_appengine_deployment_files",
            "--verbosity=debug",
        ],
    },
    {
        "name": "gcr.io/cloud-builders/gsutil",
        "args": [
            "iam",
            "ch",
            "group:${_DATASET}@healthdatanexus.ai:objectAdmin",
            "gs://${_PROJECT_ID}.appspot.com",
        ],
    },
]


START_RSTUDIO_WORKBENCH_STEPS = [
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "app",
            "versions",
            "start",
            "${_VERSION_ID}",
            "--project=${_PROJECT_ID}",
            "-q",
        ],
    }
]

UPDATE_RSTUDIO_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "vmcreation/python3.py",
            "${_SERVICE_ID}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vmcreation", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vmcreation", "apply", "-auto-approve"],
        "env": [
            "TF_VAR_machine_type=${_MACHINE_TYPE}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_dataset=${_DATASET}",
            "TF_VAR_status=RUNNING",
            "TF_VAR_region=${_REGION}",
            "TF_VAR_password=password",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_workspace_controller_project_name=${_WORKSPACE_CONTROLLER_PROJECT_NAME}",
            "TF_VAR_data_project_name=${_DATA_PROJECT_NAME}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT}",
        ],
    },
    {
        "name": "python",
        "args": [
            "python3",
            "appengine-rstudio/python3.py",
            "${_SERVICE_ID}",
            "${_SERVICE_ACCOUNT}",
            "${_MACHINE_TYPE}",
            "${_REGION}",
            "${_DISK_SIZE}",
            "",
            "${_PROJECT_ID}",
        ],
    },
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "app",
            "deploy",
            "appengine-rstudio/app.yaml",
            "--image-url=${_IMAGE_URL}",
            "--project=${_PROJECT_ID}",
            "--bucket=gs://my-app-engine-abcd1-bucket1",
            "--stop-previous-version",
        ],
    },
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "app",
            "versions",
            "delete",
            "${_VERSION_ID}",
            "--service=${_SERVICE_ID}",
            "--project=${_PROJECT_ID}",
        ],
    },
]

DESTROY_RSTUDIO_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "vmcreation/python3.py",
            "${_SERVICE_ID}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vmcreation", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vmcreation", "destroy", "-auto-approve"],
        "env": [
            "TF_VAR_machine_type=${_MACHINE_TYPE}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_dataset=${_DATASET}",
            "TF_VAR_status=RUNNING",
            "TF_VAR_region=region",
            "TF_VAR_password=password",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_workspace_controller_project_name=${_WORKSPACE_CONTROLLER_PROJECT_NAME}",
            "TF_VAR_data_project_name=${_DATA_PROJECT_NAME}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT}",
        ],
    },
    {
        "name": "python",
        "args": [
            "python3",
            "appengine-rstudio/python3.py",
            "${_SERVICE_ID}",
            "${_SERVICE_ACCOUNT}",
            "${_MACHINE_TYPE}",
            "region",
            "${_DISK_SIZE}",
            "${_BUCKET_NAME}",
            "${_PROJECT_ID}",
        ],
    },
    {
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "app",
            "services",
            "delete",
            "${_SERVICE_ID}",
            "--project=${_PROJECT_ID}",
        ],
    },
]
