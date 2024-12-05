CLONE_GITHUB_REPO = [
    {
        "id": "add_github_to_ssh_known_hosts",
        "name": "gcr.io/cloud-builders/git",
        "secret_env": ["GITHUB_SSH_KEY"],
        "entrypoint": "/bin/sh",
        "args": [
            "-c",
            'pwd && echo "$$GITHUB_SSH_KEY" >> /root/.ssh/id_rsa && chmod 400 /root/.ssh/id_rsa && ssh-keyscan -t rsa github.com > /root/.ssh/known_hosts',
        ],
        "volumes": [{"name": "ssh", "path": "/root/.ssh"}],
    },
    {
        "id": "clone_github_repo",
        "name": "gcr.io/cloud-builders/git",
        "args": [
            "clone",
            "--single-branch",
            "--branch",
            "${_TERRAFORM_BRANCH_NAME}",
            "git@github.com:${_TERRAFORM_REPO_NAME}.git",
        ],
        "secret_env": ["GITHUB_SSH_KEY"],
        "volumes": [{"name": "ssh", "path": "/root/.ssh"}],
        "wait_for": ["add_github_to_ssh_known_hosts"],
    },
]


CREATE_JUPYTER_WORKBENCH_STEPS_PARTIAL = [
    {
        "id": "jupyter_workbench_creation_setup",
        "name": "gcr.io/cloud-builders/git",
        "entrypoint": "/bin/sh",
        "args": ["-c", "ls && pwd"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_creation_set_backend_bucket",
        "name": "python",
        "args": [
            "python3",
            "workbench/jupyter/python3.py",
            "${_INSTANCE_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_creation_set_config",
        "name": "python",
        "args": [
            "python3",
            "workbench/jupyter/python4.py",
            "${_BUCKET_NAME}",
            "${_SHARING_BUCKET_IDENTIFIERS}",
            "${_SHARING_BUCKET_PERMISSIONS}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_creation_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/jupyter", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_creation_terraform_plan",
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
            "TF_VAR_workbench_type=${_WORKBENCH_TYPE}",
            "TF_VAR_sharing_bucket_identifiers=${_SHARING_BUCKET_IDENTIFIERS}",
            "TF_VAR_user_permissions_list=${_USER_PERMISSIONS_LIST}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_creation_terraform_apply_script",
        "name": "hashicorp/terraform",
        "entrypoint": "/bin/sh",
        "args": ["workbench/jupyter/terraform_apply.sh"],
        "dir_": "terraform-workbench-creation",
    },
]

CREATE_WORKSPACE_STEPS_PARTIAL = [
    {
        "id": "workspace_creation_setup",
        "name": "python",
        "args": ["python3", "project/python3.py", "${_PROJECT_ID}"],
        "wait_for": ["clone_github_repo"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_creation_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./project", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_creation_terraform_apply",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./project", "apply", "-auto-approve"],
        "env": [
            "TF_VAR_billing_account=${_BILLING_ACCOUNT}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_workspace_region=${_WORKSPACE_REGION}",
            "TF_VAR_workspace_controller_project_name=${_WORKSPACE_CONTROLLER_PROJECT_NAME}",
            "TF_VAR_user_permissions_list=${_USER_PERMISSIONS_LIST}",
            "TF_VAR_folder_id=${_GOOGLE_WORKSPACES_FOLDER_ID}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_creation_vpc_setup",
        "name": "python",
        "args": ["python3", "vpc-sp/python3.py", "${_PROJECT_ID}"],
        "wait_for": ["clone_github_repo"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_creation_vpc_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vpc-sp", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_creation_vpc_terraform_apply",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vpc-sp", "apply", "-auto-approve"],
        "env": [
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_perimeter_name=${_PERIMETER_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
]

CREATE_SHARED_WORKSPACE_STEPS_PARTIAL = [
    {
        "id": "shared_workspace_creation_setup",
        "name": "python",
        "args": [
            "python3",
            "sharing/create-sharing-project/python3.py",
            "${_PROJECT_ID}",
        ],
        "wait_for": ["clone_github_repo"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_creation_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./sharing/create-sharing-project", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_creation_terraform_apply",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./sharing/create-sharing-project", "apply", "-auto-approve"],
        "env": [
            "TF_VAR_billing_account=${_BILLING_ACCOUNT}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_email=${_EMAIL_ID}",
            "TF_VAR_sharing_folder_id=${_SHARING_FOLDER_ID}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_creation_vpc_setup",
        "name": "python",
        "args": ["python3", "vpc-sp/python3.py", "${_PROJECT_ID}"],
        "wait_for": ["clone_github_repo"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_creation_vpc_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vpc-sp", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_creation_vpc_terraform_apply",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vpc-sp", "apply", "-auto-approve"],
        "env": [
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_perimeter_name=${_PERIMETER_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
]

DESTROY_WORKSPACE_STEPS_PARTIAL = [
    {
        "id": "workspace_vpc_destruction_setup",
        "name": "python",
        "args": ["python3", "vpc-sp/python3.py", "${_PROJECT_ID}"],
        "wait_for": ["clone_github_repo"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_destruction_vpc_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vpc-sp", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_destruction_vpc_terraform_destroy",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vpc-sp", "destroy", "-auto-approve"],
        "env": [
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_perimeter_name=${_PERIMETER_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_destruction_setup",
        "name": "python",
        "args": ["python3", "project/python3.py", "${_PROJECT_ID}"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_destruction_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./project", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "workspace_destruction_terraform_destroy",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./project", "destroy", "-auto-approve"],
        "env": [
            "TF_VAR_billing_account=${_BILLING_ACCOUNT}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_emailid=${_EMAIL_ID}",
            "TF_VAR_workspace_region=${_WORKSPACE_REGION}",
            "TF_VAR_workspace_controller_project_name=${_WORKSPACE_CONTROLLER_PROJECT_NAME}",
            "TF_VAR_folder_id=${_GOOGLE_WORKSPACES_FOLDER_ID}",
        ],
        "dir_": "terraform-workbench-creation",
    },
]

DESTROY_SHARED_WORKSPACE_STEPS_PARTIAL = [
    {
        "id": "shared_workspace_destruction_setup",
        "name": "python",
        "args": [
            "python3",
            "sharing/create-sharing-project/python3.py",
            "${_PROJECT_ID}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_destruction_vpc_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vpc-sp", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_destruction_vpc_terraform_destroy",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./vpc-sp", "destroy", "-auto-approve"],
        "env": [
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_perimeter_name=${_PERIMETER_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_destruction_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./sharing/create-sharing-project", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "shared_workspace_destruction_terraform_destroy",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./sharing/create-sharing-project", "destroy", "-auto-approve"],
        "env": [
            "TF_VAR_billing_account=${_BILLING_ACCOUNT}",
            "TF_VAR_project_id=${_PROJECT_ID}",
            "TF_VAR_email=${_EMAIL_ID}",
            "TF_VAR_sharing_folder_id=${_SHARING_FOLDER_ID}",
        ],
        "dir_": "terraform-workbench-creation",
    },
]


UPDATE_JUPYTER_WORKBENCH_STEPS_PARTIAL = [
    {
        "id": "jupyter_workbench_update_set_backend_bucket",
        "name": "python",
        "args": [
            "python3",
            "workbench/jupyter/python3.py",
            "${_INSTANCE_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_update_set_config",
        "name": "python",
        "args": [
            "python3",
            "workbench/jupyter/python4.py",
            "${_BUCKET_NAME}",
            "${_SHARING_BUCKET_IDENTIFIERS}",
            "${_SHARING_BUCKET_PERMISSIONS}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_gcloud_stop_instance",
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "workbench",
            "instances",
            "stop",
            "${_INSTANCE_NAME}",
            "--location=${_ZONE}",
            "--project",
            "${_PROJECT_ID}",
        ],
    },
    {
        "id": "jupyter_workbench_gcloud_update_instance",
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "workbench",
            "instances",
            "update",
            "${_INSTANCE_NAME}",
            "--machine-type=${_MACHINE_TYPE}",
            "--location=${_ZONE}",
            "--project",
            "${_PROJECT_ID}",
        ],
    },
    {
        "id": "jupyter_workbench_gcloud_start_instance",
        "name": "gcr.io/cloud-builders/gcloud",
        "args": [
            "workbench",
            "instances",
            "start",
            "${_INSTANCE_NAME}",
            "--location=${_ZONE}",
            "--project",
            "${_PROJECT_ID}",
        ],
    },
]

DESTROY_JUPYTER_WORKBENCH_STEPS_PARTIAL = [
    {
        "id": "jupyter_workbench_destruction_set_backend_bucket",
        "name": "python",
        "args": [
            "python3",
            "workbench/jupyter/python3.py",
            "${_INSTANCE_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_destruction_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/jupyter", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "jupyter_workbench_destruction_terraform_destroy",
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
            "TF_VAR_workbench_type=${_WORKBENCH_TYPE}",
            "TF_VAR_sharing_bucket_identifiers=${_SHARING_BUCKET_IDENTIFIERS}",
        ],
        "dir_": "terraform-workbench-creation",
    },
]


CREATE_RSTUDIO_WORKBENCH_STEPS_PARTIAL = [
    {
        "id": "rstudio_workbench_creation_set_backend_bucket",
        "name": "python",
        "args": [
            "python3",
            "workbench/rstudio/python3.py",
            "${_INSTANCE_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_creation_set_config",
        "name": "python",
        "args": [
            "python3",
            "workbench/rstudio/python4.py",
            "${_BUCKET_NAME}",
            "${_SHARING_BUCKET_IDENTIFIERS}",
            "${_SHARING_BUCKET_PERMISSIONS}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_creation_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_creation_terraform_plan",
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
            "TF_VAR_brand_name=${_BRAND_NAME}",
            "TF_VAR_workbench_type=${_WORKBENCH_TYPE}",
            "TF_VAR_sharing_bucket_identifiers=${_SHARING_BUCKET_IDENTIFIERS}",
            "TF_VAR_user_permissions_list=${_USER_PERMISSIONS_LIST}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_creation_terraform_apply_script",
        "name": "hashicorp/terraform",
        "entrypoint": "/bin/sh",
        "args": ["workbench/rstudio/terraform_apply.sh"],
        "dir_": "terraform-workbench-creation",
    },
]


UPDATE_RSTUDIO_WORKBENCH_STEPS_PARTIAL = [
    {
        "id": "rstudio_workbench_update_set_backend_bucket",
        "name": "python",
        "args": [
            "python3",
            "workbench/rstudio/python3.py",
            "${_INSTANCE_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_update_set_config",
        "name": "python",
        "args": [
            "python3",
            "workbench/rstudio/python4.py",
            "${_BUCKET_NAME}",
            "${_SHARING_BUCKET_IDENTIFIERS}",
            "${_SHARING_BUCKET_PERMISSIONS}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_update_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_update_terraform_apply",
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
            "TF_VAR_brand_name=${_BRAND_NAME}",
            "TF_VAR_workbench_type=${_WORKBENCH_TYPE}",
            "TF_VAR_sharing_bucket_identifiers=${_SHARING_BUCKET_IDENTIFIERS}",
            "TF_VAR_user_permissions_list=${_USER_PERMISSIONS_LIST}",
        ],
        "dir_": "terraform-workbench-creation",
    },
]

DESTROY_RSTUDIO_WORKBENCH_STEPS_PARTIAL = [
    {
        "id": "rstudio_workbench_destruction_set_backend_bucket",
        "name": "python",
        "args": [
            "python3",
            "workbench/rstudio/python3.py",
            "${_INSTANCE_NAME}",
        ],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_destruction_terraform_init",
        "name": "hashicorp/terraform",
        "args": ["-chdir=./workbench/rstudio", "init", "-reconfigure"],
        "dir_": "terraform-workbench-creation",
    },
    {
        "id": "rstudio_workbench_destruction_terraform_destroy",
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
            "TF_VAR_brand_name=${_BRAND_NAME}",
            "TF_VAR_workbench_type=${_WORKBENCH_TYPE}",
            "TF_VAR_sharing_bucket_identifiers=${_SHARING_BUCKET_IDENTIFIERS}",
        ],
        "dir_": "terraform-workbench-creation",
    },
]

CREATE_JUPYTER_WORKBENCH_STEPS = [
    *CLONE_GITHUB_REPO,
    *CREATE_JUPYTER_WORKBENCH_STEPS_PARTIAL,
]

DESTROY_JUPYTER_WORKBENCH_STEPS = [
    *CLONE_GITHUB_REPO,
    *DESTROY_JUPYTER_WORKBENCH_STEPS_PARTIAL,
]

CREATE_WORKSPACE_STEPS = [
    *CLONE_GITHUB_REPO,
    *CREATE_WORKSPACE_STEPS_PARTIAL,
]

CREATE_SHARED_WORKSPACE_STEPS = [
    *CLONE_GITHUB_REPO,
    *CREATE_SHARED_WORKSPACE_STEPS_PARTIAL,
]

DESTROY_WORKSPACE_STEPS = [
    *CLONE_GITHUB_REPO,
    *DESTROY_WORKSPACE_STEPS_PARTIAL,
]

DESTROY_SHARED_WORKSPACE_STEPS = [
    *CLONE_GITHUB_REPO,
    *DESTROY_SHARED_WORKSPACE_STEPS_PARTIAL,
]

UPDATE_JUPYTER_WORKBENCH_STEPS = [
    *CLONE_GITHUB_REPO,
    *UPDATE_JUPYTER_WORKBENCH_STEPS_PARTIAL,
]

CREATE_RSTUDIO_WORKBENCH_STEPS = [
    *CLONE_GITHUB_REPO,
    *CREATE_RSTUDIO_WORKBENCH_STEPS_PARTIAL,
]

UPDATE_RSTUDIO_WORKBENCH_STEPS = [
    *CLONE_GITHUB_REPO,
    *UPDATE_RSTUDIO_WORKBENCH_STEPS_PARTIAL,
]

DESTROY_RSTUDIO_WORKBENCH_STEPS = [
    *CLONE_GITHUB_REPO,
    *DESTROY_RSTUDIO_WORKBENCH_STEPS_PARTIAL,
]
