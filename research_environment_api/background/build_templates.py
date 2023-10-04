CREATE_JUPYTER_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "workbench/jupyter/python3.py",
            "${_INSTANCE_NAME}",
        ],
    },
    {
        "name": "python",
        "args": ["python3", "workbench/jupyter/python4.py", "${_BUCKET_NAME}"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/jupyter", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/jupyter", "plan", "-out=tfplan.out"],
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
            "TF_VAR_startup_script_bucket=${_JUPYTER_STARTUP_SCRIPT_BUCKET}",
            "TF_VAR_name=${_INSTANCE_NAME}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT_NAME}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "entrypoint": "/bin/sh",
        "args": ["workbench/jupyter/terraform_apply.sh"],
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
            "workbench/jupyter/python3.py",
            "${_INSTANCE_NAME}",
        ],
    },
    {
        "name": "python",
        "args": ["python3", "workbench/jupyter/python4.py", "${_BUCKET_NAME}"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/jupyter", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/jupyter", "apply", "-auto-approve"],
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
            "TF_VAR_startup_script_bucket=${_JUPYTER_STARTUP_SCRIPT_BUCKET}",
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
            "workbench/jupyter/python3.py",
            "${_INSTANCE_NAME}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/jupyter", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/jupyter", "destroy", "-auto-approve"],
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
            "TF_VAR_startup_script_bucket=${_JUPYTER_STARTUP_SCRIPT_BUCKET}",
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


CREATE_RSTUDIO_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "workbench/rstudio/python3.py",
            "${_INSTANCE_NAME}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "plan", "-out=tfplan.out"],
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
            "TF_VAR_startup_script_bucket=${_RSTUDIO_STARTUP_SCRIPT_BUCKET}",
            "TF_VAR_name=${_INSTANCE_NAME}",
            "TF_VAR_network_name=${_NETWORK_NAME}",
            "TF_VAR_dns_project=${_RSTUDIO_DNS_PROJECT}",
            "TF_VAR_rstudio_domain_name=${_RSTUDIO_DOMAIN_NAME}",
            "TF_VAR_dns_zone=${_RSTUDIO_DNS_ZONE}",
            "TF_VAR_private_key=${_RSTUDIO_SSL_PRIVATE_KEY}",
            "TF_VAR_certificate=${_RSTUDIO_SSL_CERTIFICATE}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT_NAME}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "entrypoint": "/bin/sh",
        "args": ["workbench/rstudio/terraform_apply.sh"],
    },
]


UPDATE_RSTUDIO_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "workbench/rstudio/python3.py",
            "${_INSTANCE_NAME}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "apply", "-auto-approve"],
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
            "TF_VAR_startup_script_bucket=${_RSTUDIO_STARTUP_SCRIPT_BUCKET}",
            "TF_VAR_name=${_INSTANCE_NAME}",
            "TF_VAR_network_name=${_NETWORK_NAME}",
            "TF_VAR_dns_project=${_RSTUDIO_DNS_PROJECT}",
            "TF_VAR_rstudio_domain_name=${_RSTUDIO_DOMAIN_NAME}",
            "TF_VAR_dns_zone=${_RSTUDIO_DNS_ZONE}",
            "TF_VAR_private_key=${_RSTUDIO_SSL_PRIVATE_KEY}",
            "TF_VAR_certificate=${_RSTUDIO_SSL_CERTIFICATE}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT_NAME}",
        ],
    },
]

DESTROY_RSTUDIO_WORKBENCH_STEPS = [
    {
        "name": "python",
        "args": [
            "python3",
            "workbench/rstudio/python3.py",
            "${_INSTANCE_NAME}",
        ],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "init", "-reconfigure"],
    },
    {
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "destroy", "-auto-approve"],
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
            "TF_VAR_startup_script_bucket=${_RSTUDIO_STARTUP_SCRIPT_BUCKET}",
            "TF_VAR_name=${_INSTANCE_NAME}",
            "TF_VAR_network_name=${_NETWORK_NAME}",
            "TF_VAR_dns_project=${_RSTUDIO_DNS_PROJECT}",
            "TF_VAR_rstudio_domain_name=${_RSTUDIO_DOMAIN_NAME}",
            "TF_VAR_dns_zone=${_RSTUDIO_DNS_ZONE}",
            "TF_VAR_private_key=${_RSTUDIO_SSL_PRIVATE_KEY}",
            "TF_VAR_certificate=${_RSTUDIO_SSL_CERTIFICATE}",
            "TF_VAR_service_account_name=${_SERVICE_ACCOUNT_NAME}",
        ],
    },
]
