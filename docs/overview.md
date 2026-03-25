# Research Environment API – Developer Overview

## What is this?

This API manages cloud-based research environments on Google Cloud Platform. It provisions and controls:

- **Workspaces** – isolated GCP projects per researcher
- **Workbenches** – compute instances inside workspaces (Jupyter, Collaborative, or RStudio)
- **Shared buckets** – GCS buckets for data collaboration between researchers
- **Billing accounts** – GCP billing account management and assignment
- **Cloud identities** – Google Workspace user provisioning

The stack is **Flask + Celery + SQLAlchemy (PostgreSQL)**. Long-running GCP operations (creating VMs) are handled asynchronously via Celery task chains.

---

## Project Setup

### Prerequisites

```bash
brew install --cask google-cloud-sdk
brew install sops
```

Python >= 3.11 is required.

```bash
python3.11 -m venv venv/python
source venv/python/bin/activate
pip install -r requirements.txt
```

### Credentials

The app uses a GCP service account to interact with GCP APIs. Credentials in the repo are sops-encrypted (GCP Cloud KMS).

1. Get `credentials.json` from 1Password (or ask a teammate).
2. If you have GCP access, you can decrypt the stored credentials:
   ```bash
   sops --decrypt credentials/credentials.enc.json > credentials.json
   ```
3. Set `SERVICE_ACCOUNT_CREDENTIALS_PATH` in your `.env` to point to the decrypted file.

> **Important:** Never commit unencrypted credential files. Only `credentials/*.enc.json` should be pushed.

### Environment Variables

Create a `.env` file. The minimum required variables to run the app locally:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql://user:password@localhost:5432/research_env

# GCP project/org configuration
PROJECT_ID=your-gcp-project-id
ORGANIZATION_ID=your-org-id
BILLING_ACCOUNT_CREATOR_GROUP_ID=your-group-id
VPC_SECURE_PERIMETER_NAME=your-perimeter

# Terraform source repo
TERRAFORM_BRANCH_NAME=main
TERRAFORM_REPO_NAME=your-infra-repo

# Workbench startup scripts (GCS paths)
JUPYTER_STARTUP_SCRIPT=gs://your-bucket/jupyter.sh
RSTUDIO_STARTUP_SCRIPT=gs://your-bucket/rstudio.sh

# Cloud Build
CLOUD_BUILD_SERVICE_ACCOUNT_NAME=builder@your-project.iam.gserviceaccount.com
RSTUDIO_IMAGE_URL=gcr.io/your-project/rstudio

# Networking
DATA_PROJECT_NAME=your-data-project
NETWORK_NAME=default

# RStudio DNS
RSTUDIO_DNS_PROJECT=your-dns-project
RSTUDIO_DNS_ZONE=your-dns-zone
RSTUDIO_DOMAIN_NAME=your-domain.com
RSTUDIO_CERTIFICATE_SECRET_ID=your-cert-secret

# Sharing
SHARING_FOLDER_ID=your-folder-id
WORKBENCHES_PARENT_PROJECT_ID=your-parent-project

# Misc (can use placeholders for initial local setup)
GCP_SIGNED_URL_EXPIRATION_TIME=3600
GCP_CORS_ALLOWED_ORIGINS=http://localhost:3000
GITHUB_SSH_KEY_KSM_ID=your-ssh-key-id
MONITORING_CSV_EXPORTS_ROOT_BUCKET=any-placeholder-value

# Admin panel
ADMIN_PANEL_USERNAME=admin
ADMIN_PANEL_PASSWORD=yourpassword
ADMIN_PANEL_CACHE_TTL=300

# Credentials
SERVICE_ACCOUNT_CREDENTIALS_PATH=/path/to/credentials.json

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Caching
CACHE_TYPE=SimpleCache
```

> `MONITORING_CSV_EXPORTS_ROOT_BUCKET` does not need to point to a real bucket for initial setup – any non-empty string works.

### Database

```bash
alembic upgrade head
```

---

## Core Concepts

### Workspace

A **Workspace** is a GCP Project that represents an isolated research environment for a user. Key properties:

- Owned by a single researcher (`cloud_identity_username`)
- Has an attached GCP billing account
- Contains workbenches (compute instances)
- Can be accessible or inaccessible depending on billing status

Workspaces are created/deleted via **Terraform** executed through Cloud Build. The API triggers a Cloud Build job and polls for completion.

### Workbench

A **Workbench** is a cloud compute instance inside a workspace. Three types are supported:

| Type | GCP Resource | Use Case |
|------|-------------|----------|
| `jupyter` | Vertex AI Notebook | Jupyter notebooks |
| `collaborative` | Vertex AI Notebook (collab mode) | Shared Jupyter sessions |
| `rstudio` | Compute Engine VM | RStudio Server |

Workbenches support GPU accelerators, collaborators (other users granted IAM access), and can be started/stopped/updated. State is tracked in the database.

### Shared Bucket

A **Shared Bucket** is a GCS bucket for data sharing between researchers. Access is controlled via IAM:
- `READ` – viewer role
- `READ_WRITE` – admin role

Sharing state transitions: `PENDING → SHARED → REVOKED`.

### Workflow (Operation)

A **Workflow** represents an in-progress asynchronous operation (workbench create, workspace delete, etc.). The frontend polls `GET /workflow/<workflow_id>` to track progress. Workflows are stored in the database with statuses: `IN_PROGRESS`, `SUCCESS`, `FAILED`.

---

## Workflows

### How Workbench Creation Works (End to End)

This is the most complex flow in the system and illustrates how all the pieces fit together.

**1. HTTP request arrives**

`POST /workbench` → `workbench_management/views.py` → `workbench_management/services.py` → `workbench_management/schedulers.py`

The scheduler:
- Generates a unique workbench name (e.g. `jupyter-{dataset_id[:10]}-{5_random_chars}`)
- Selects a GCP zone (with fallback zones for retry)
- Builds a **Cloud Build configuration** object (via `build_templates.py`) with 30+ Terraform variable substitutions
- Creates a `WorkbenchActivity` record in the DB with status `IN_PROGRESS` and a new UUID
- **Returns that UUID immediately** to the HTTP caller (this is the operation/workflow ID)
- Dispatches a Celery task chain

**2. Celery chain runs asynchronously**

```
start_cloud_build
  → check_operation_status         (polls every 30s until done)
  → process_cloud_build_result     (handles errors / zone fallback)
  → check_vertex_ai_setup_status   (polls instance metadata for "proxy-url")
     or check_rstudio_page_status  (HTTP polls the RStudio URL)
  → add_monitoring_entry           (records usage start in DB)
  → set_workflow_status            (marks WorkbenchActivity SUCCESS, emits WebSocket event)
```

For RStudio, `check_rstudio_page_status` additionally creates a DNS record and waits for the RStudio server HTTP endpoint to respond.

**3. Cloud Build runs Terraform**

`start_cloud_build` submits a job to GCP Cloud Build. The build steps:
1. Clone the Terraform repo from GitHub (SSH key fetched from Secret Manager)
2. `terraform init` – configure backend bucket
3. `terraform plan` – using `TF_VAR_*` substitutions (machine type, zone, user email, bucket, GPU, etc.)
4. `terraform apply` – creates the GCE/Vertex AI instance, service account, IAM bindings, and mounts persistent disks

**4. Caller polls for completion**

The frontend polls `GET /workflow/<uuid>` until the status is `SUCCESS` or `FAILED`. On completion, a WebSocket `workflow_update` event is also emitted.

**Error handling:**
- If Cloud Build fails and fallback zones are configured, the chain restarts the entire workflow in the next zone.
- Unrecoverable failures set `build_error_information` on the activity and mark it `FAILED`.
- A 30-minute background task (`check_and_process_cloud_build_operation`) catches builds that get stuck.

---

### Workspace Creation Flow

Simpler than workbench – same Cloud Build / Terraform pattern but for creating/deleting an entire GCP project:

```
POST /workspace
  → workspace_management/services.py
  → schedulers.create_workspace()
     - Creates WorkbenchActivity (UUID returned to caller)
     - Cloud Build config runs workspace Terraform
  → Celery chain:
       start_cloud_build
         → check_operation_status
         → process_cloud_build_result
         → set_workflow_status
```

---

### Terraform

Terraform is **not run locally by the API**. Instead, the API submits Cloud Build jobs that run Terraform inside GCP's managed build environment. The Terraform code lives in a separate infrastructure repo (`TERRAFORM_REPO_NAME`), and the API clones that repo at `TERRAFORM_BRANCH_NAME` during each build.

The `terraform/` directory in this repo is for the **API's own infrastructure** (Cloud Run service, Redis, Cloud SQL, etc.) – used when deploying the API itself, not when provisioning researcher resources.

---

### Scheduled Background Tasks

| Schedule | Task |
|----------|------|
| Weekly | Export active users per dataset → GCS bucket |
| Weekly | Export dataset total usage time → GCS bucket |
| Every 6 hours | Mark stale (long-running) workbenches as deleted in monitoring |

Tasks retry up to 10 times with exponential backoff on transient failures.

---

## API Structure

Blueprints registered at:

| Prefix | Module | Purpose |
|--------|--------|---------|
| `/identity` | identity_management | Provision Google Workspace users |
| `/billing` | billing_management | Manage billing accounts |
| `/workspace` | workspace_management | Create/delete research workspaces |
| `/workbench` | workbench_management | Manage compute instances |
| `/workflow` | workflow | Poll async operation status |
| `/sharing` | sharing_management | GCS bucket sharing |
| `/group` | user_group_management | Cloud Identity groups |
| `/monitoring` | monitoring_management | Usage tracking and CSV exports |
| `/admin` | admin_panel | Admin UI (Basic Auth protected) |
| `/docs` | – | Swagger UI |

---

## Authentication

- Most endpoints use `@validate_token` – validates a Google OAuth2 ID token from the `Authorization: Bearer <token>` header.
- The admin panel (`/admin`) uses HTTP Basic Auth (`ADMIN_PANEL_USERNAME` / `ADMIN_PANEL_PASSWORD`).

---

## Deploying to Staging

### 1. Build and push the Docker image

```bash
# Build for linux/amd64 (required for Cloud Run)
docker build \
  -t northamerica-northeast2-docker.pkg.dev/research-environment-api-dev/research-environment-api/core:`git rev-parse HEAD` \
  . --platform=linux/amd64

# Push (first-time auth setup below if needed)
docker push northamerica-northeast2-docker.pkg.dev/research-environment-api-dev/research-environment-api/core:`git rev-parse HEAD`
```

Note the full image digest from the last line of push output, e.g.:
```
297b6835e8b5...: digest: sha256:1fae518... size: 856
```
The tag is the part before `:` – you'll need it for Terraform.

**First-time Docker auth setup:**
```bash
gcloud auth login
gcloud auth configure-docker northamerica-northeast2-docker.pkg.dev
# Accept with Y when prompted
```
If you get permission errors, set the required permissions in the GCP Console for Artifact Registry first.

### 2. Apply with Terraform

```bash
cd terraform

# Get credentials and variables from 1Password (use DEV secrets)
# - credentials.json  → save as terraform/credentials.json
# - terraform.tfvars  → save as terraform/terraform.tfvars
#   (tfvars in 1Password may be incomplete – verify with a teammate)

# Update image_tag in terraform.tfvars to the tag from step 1

terraform init
terraform workspace select dev   # switch to dev workspace if needed
terraform plan
terraform apply                  # confirm when prompted
```

---

## Key Files

| File | Purpose |
|------|---------|
| `research_environment_api/web/app.py` | Flask app factory, blueprint registration |
| `research_environment_api/wsgi.py` | WSGI entry point |
| `research_environment_api/worker.py` | Celery worker entry point |
| `research_environment_api/background/tasks.py` | All Celery task definitions |
| `research_environment_api/background/workflows.py` | Celery chain definitions |
| `research_environment_api/background/build_templates.py` | Cloud Build config builders |
| `research_environment_api/web/decorators.py` | Auth decorators |
| `research_environment_api/tests/helpers/test_env.py` | All env vars with test values |
| `alembic/versions/` | Database migration history |
| `terraform/` | API infrastructure (Cloud Run, Redis, Cloud SQL) |
| `credentials/` | sops-encrypted service account credentials |
