# Research Environment API — Developer Documentation

---

## Table of Contents

1. [Project Purpose](#1-project-purpose)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Repository Layout](#3-repository-layout)
4. [Prerequisites and Credentials Setup](#4-prerequisites-and-credentials-setup)
5. [Database Models](#5-database-models)
6. [Core Concepts](#6-core-concepts)
7. [End-to-End Request Flows](#7-end-to-end-request-flows)
8. [API Auth — How Token Validation Works](#8-api-auth--how-token-validation-works)
9. [URL Routing — Exhaustive Reference](#9-url-routing--exhaustive-reference)
10. [View Layer](#10-view-layer)
11. [Access Control and Decorator Chain](#11-access-control-and-decorator-chain)
12. [Background Tasks and Signals](#12-background-tasks-and-signals)
13. [Email Notifications](#13-email-notifications)
14. [Entity and Dataclass Types](#14-entity-and-dataclass-types)
15. [Admin Console](#15-admin-console)
16. [Fixtures and Seed Data](#16-fixtures-and-seed-data)
17. [Error Handling Utilities](#17-error-handling-utilities)
18. [External Integrations and Services](#18-external-integrations-and-services)
19. [Testing Approach](#19-testing-approach)
20. [CI/CD](#20-cicd)
21. [Common Failure Modes](#21-common-failure-modes)
22. [Environment Variables Reference](#22-environment-variables-reference)
23. [Known Bugs](#23-known-bugs)
24. [Glossary](#24-glossary)

---

## 1. Project Purpose

This service is the backend API for the **Health Data Nexus (HDN)** Research Environment platform. It exposes a REST API that the HDN frontend (React SPA) calls to:

- Create and manage Google Cloud **workspaces** (GCP projects) on behalf of researchers.
- Provision and lifecycle-manage **workbenches** — Jupyter notebooks, RStudio instances, and collaborative compute environments running on Google Compute Engine / Vertex AI Notebooks.
- Manage **Cloud Identity** accounts (Google Workspace users).
- Control **billing account** access per workspace.
- Manage **shared storage buckets** between researchers.
- Manage **user groups** (Cloud Identity groups) and their IAM roles.
- Monitor workbench usage and export reports.
- Stream live workflow status via Server-Sent Events.

All Google Cloud provisioning is done via **Cloud Build pipelines** triggered by this service. No GCP resources are created directly from Python — everything goes through Cloud Build, which runs the Terraform in a sibling repository.

---

## 2. High-Level Architecture

```
                         ┌──────────────────────────────────────────────┐
                         │              Client (React SPA / HDN)         │
                         └────────────────────┬─────────────────────────┘
                                              │ HTTPS + Bearer token (Google OIDC)
                                              ▼
                         ┌──────────────────────────────────────────────┐
                         │          Gunicorn (WSGI, N workers)           │
                         │   research_environment_api.wsgi:app           │
                         └────────────────────┬─────────────────────────┘
                                              │
                         ┌────────────────────▼─────────────────────────┐
                         │              Flask Application                │
                         │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
                         │  │/identity │  │/billing  │  │/workspace │  │
                         │  └──────────┘  └──────────┘  └───────────┘  │
                         │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
                         │  │/workbench│  │/workflow │  │/sharing   │  │
                         │  └──────────┘  └──────────┘  └───────────┘  │
                         │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
                         │  │/group    │  │/monitoring│  │/admin     │  │
                         │  └──────────┘  └──────────┘  └───────────┘  │
                         │  ┌──────────┐                               │
                         │  │/docs     │  (Swagger UI, auto-generated)  │
                         │  └──────────┘                               │
                         └──┬────────────────────────────┬─────────────┘
                            │                            │
              ┌─────────────▼──────┐      ┌─────────────▼──────────────┐
              │   PostgreSQL DB    │      │   Redis (broker + backend) │
              │  (SQLAlchemy ORM)  │      │   + Pub/Sub for SSE        │
              └─────────────┬──────┘      └─────────────┬──────────────┘
                            │                           │
              ┌─────────────▼──────────────────────────▼──────────────┐
              │                  Celery Worker                         │
              │  ┌────────────┐  ┌──────────────┐  ┌───────────────┐ │
              │  │schedulers  │→ │  workflows   │→ │   tasks       │ │
              │  └────────────┘  └──────────────┘  └───────┬───────┘ │
              └──────────────────────────────────────────────┼────────┘
                                                             │ Cloud Build API
                                                ┌────────────▼──────────────┐
                                                │   Google Cloud Build       │
                                                │  (runs Terraform steps)    │
                                                └────────────┬──────────────┘
                                                             │ Terraform
                                          ┌──────────────────▼──────────────────┐
                                          │         Google Cloud Platform         │
                                          │  Compute Engine · Vertex AI           │
                                          │  Cloud Storage · Cloud Identity       │
                                          │  Billing · IAM · Resource Manager     │
                                          │  Secret Manager · Service Usage       │
                                          │  Cloud Monitoring                     │
                                          └──────────────────────────────────────┘
```

**Request flow summary:**
1. Client sends an HTTPS request with a Google OIDC Bearer token.
2. Flask blueprint handler validates the token via `@validate_token`.
3. Handler calls a service function in `modules/` which may call GCP directly (for read operations) or dispatch to a Celery chain (for mutations).
4. Write operations create a `WorkbenchActivity` DB row, then trigger a Cloud Build job through the GCP Cloud Build API.
5. The Celery task polls for job completion, then writes the final status back to PostgreSQL and publishes a message to Redis.
6. The client receives the final status either by polling `/workflow/<id>` or via the SSE stream at `/monitoring/events`.

---

## 3. Repository Layout

```
research-environment-api-top-folder/
│
├── research_environment_api/        # Main Python package (see §3.1)
│
├── alembic/                         # Database migrations
│   ├── env.py                       # Migration runner; loads app config to get the engine
│   ├── script.py.mako               # Template for new migration files
│   └── versions/                    # 6 migration scripts (chronological chain)
│
├── docs/
│   └── testing.md                   # Developer testing guide
│
├── terraform/                       # Terraform for infra (secrets, sops vars, lock file)
│
├── .github/workflows/               # GitHub Actions CI
│   ├── black.yml                    # Code style check
│   ├── unit-tests.yml               # Unit test suite
│   └── integration-tests.yml        # Integration test suite
│
├── Dockerfile                       # Production image (Python 3.11-slim + gunicorn)
├── Makefile                         # Dev shortcuts: test, coverage, etc.
├── pytest.ini                       # Test discovery + marker + coverage config
├── alembic.ini                      # Alembic DB URL placeholder
├── requirements.txt                 # Pinned dependencies (only this file is used)
├── celery_endpoint.sh               # Starts celery worker + beat locally
├── flower_endpoint.sh               # Starts Celery Flower monitoring UI
├── grant_privileges.sh              # One-shot psql grant for load-test DB setup
├── README.md                        # Cloud SQL setup, sops credential notes
│
├── credentials-api.json             # ⚠ Service account JSON checked into repo (dev)
├── credentials-api-prod.json        # ⚠ Service account JSON checked into repo (prod)
├── research-environment-api-dev-*.json  # ⚠ More SA credentials
├── workspace-controller-dev-*.json  # ⚠ Historical artifact (see note below)
├── credentials/dev/                 # sops-encrypted credentials
├── credentials/prod/                # sops-encrypted credentials
│
└── dump.rdb                         # ⚠ Redis snapshot — local dev artifact, not committed intentionally
```

> **`workspace-controller-dev-*.json` and `workspace-controller-repo/`** are historical artifacts from an earlier architecture. The active backend is an external service configured via `settings.CLOUD_RESEARCH_ENVIRONMENTS_API_URL`. All GCP work goes through that external API, never directly from this service's Django layer. In the Flask service, no such variable is referenced — Cloud Build is triggered directly.

### 3.1 `research_environment_api/` layout

```
research_environment_api/
│
├── __init__.py          # Empty (0 bytes)
├── wsgi.py              # Flask entry point — app factory + global error handler
├── worker.py            # Celery entry point — creates celery app
│
├── background/          # Celery layer
│   ├── app.py           # create_celery(), beat schedule, JSON log formatter
│   ├── tasks.py         # All @shared_task definitions
│   ├── workflows.py     # chain() factory functions (one per operation type)
│   ├── schedulers.py    # Orchestration: creates DB row, clears cache, fires workflow
│   ├── builds.py        # Constructs cloudbuild_v1.Build objects
│   ├── build_templates.py  # Cloud Build step lists (30 KB)
│   ├── operations.py    # Operation pollers (GCE zone ops, Cloud Build ops, Vertex AI ops)
│   ├── constants.py     # AVAILABLE_ZONES, CLOUD_BUILD_ERROR_MESSAGE
│   └── enums.py         # BuildType, WorkflowStatus, OperationStatus, InstanceType
│
├── library/             # Low-level GCP client wrappers
│   └── google/
│       ├── billing.py   # BillingClient — billing account IAM management
│       ├── delegation.py  # domain_delegate_credentials()
│       └── workspace.py # WorkspaceClient — Cloud Identity user/group creation
│
├── modules/             # Pure business logic (no Flask imports)
│   ├── app.py           # Application singleton
│   ├── config.py        # Config dataclass; reads all env vars; builds GCP clients
│   ├── db.py            # SQLAlchemy engine factories
│   ├── model.py         # ScopedModel base class
│   ├── logger.py        # Module-level logger
│   ├── common/
│   │   └── error_handlers.py  # ServiceError dataclass + safe_google_service_call()
│   ├── helpers/exports/
│   │   └── helpers.py   # CSV creation + GCS upload
│   ├── admin_management/
│   │   └── services.py  # ⚠ DEAD CODE — duplicates admin_panel_management/services.py
│   ├── admin_panel_management/
│   │   ├── services.py  # Celery task inspection, admin auth, workbench activity queries
│   │   ├── cache.py     # In-memory Celery inspector cache (TTL-based)
│   │   ├── utils.py     # Task state helpers (get/force state via AsyncResult)
│   │   └── entities.py  # Task, TaskStatus, WorkerStats dataclasses
│   ├── billing_management/
│   │   ├── services.py  # list/share/revoke billing account access
│   │   ├── entities.py  # BillingAccount dataclass
│   │   └── enums.py     # BillingAccountRole
│   ├── identity_management/
│   │   ├── services.py  # provision_cloud_identity() — creates GWS user + adds to group
│   │   ├── entities.py  # CloudIdentityCreation dataclass
│   │   └── exceptions.py  # CloudIdentityAlreadyConfiguredError, etc.
│   ├── monitoring_management/
│   │   ├── services.py  # SSE stream, usage time aggregation, quota checks
│   │   ├── monitoring.py  # Active workflow queries (reads WorkbenchActivity)
│   │   ├── models.py    # WorkbenchActivity, WorkbenchMonitoringData ORM models
│   │   ├── entities.py  # QuotaInfo, GeneralQuotaMetrics, monitoring dataclasses
│   │   └── exceptions.py  # QuotaExceededError
│   ├── sharing_management/
│   │   ├── services.py  # Shared bucket CRUD + IAM + signed URL generation
│   │   ├── entities.py  # SharedBucketCreation and related dataclasses
│   │   ├── enums.py     # IamSharingRole, SharingState, BucketPermissions
│   │   └── models.py    # SharingData ORM model
│   ├── user_group_management/
│   │   ├── services.py  # Cloud Identity group CRUD + IAM role management
│   │   ├── entities.py  # UserGroupCreation, GoogleRole dataclasses
│   │   └── exceptions.py  # GoogleGroupAlreadyExists
│   ├── workbench_management/
│   │   ├── services.py  # Workbench list/create/stop/start/update/destroy + collaborators
│   │   ├── entities.py  # Workbench, WorkbenchCreate and related dataclasses
│   │   ├── models.py    # WorkbenchCollaboratorData ORM model
│   │   └── utils.py     # Machine type maps, IAM binding helpers
│   └── workspace_management/
│       ├── services.py  # Workspace list/create/delete + billing update
│       └── entities.py  # Workspace, SimplifiedWorkspace, EntityScaffolding dataclasses
│
├── web/                 # Flask layer (blueprints)
│   ├── app.py           # create_app() — registers blueprints, CORS, caching, apispec
│   ├── config.py        # build_config() returns CACHE_TYPE from env
│   ├── cache.py         # Flask-Caching Cache() singleton
│   ├── decorators.py    # @validate_token, @validate_admin_page_auth
│   ├── websocket.py     # Empty file — placeholder, never used
│   ├── templates/admin_panel/  # Jinja2 templates for admin UI only
│   └── {blueprint_name}/      # One package per bounded context
│       ├── __init__.py  # Blueprint object + imports views
│       ├── views.py     # Route handlers
│       └── schemas.py   # Marshmallow schemas (request/response)
│
└── tests/
    ├── helpers/
    │   └── test_env.py  # test_env_vars() — returns dict of all required env vars
    ├── unit/            # Pure unit tests (no I/O)
    └── integration/     # Integration tests (real Postgres + fake GCS via Testcontainers)
```

---

## 4. Prerequisites and Credentials Setup

### Runtime prerequisites

| Dependency | Version | Notes |
|---|---|---|
| Python | 3.11 | Required by Dockerfile and CI |
| PostgreSQL | 13+ | Primary database |
| Redis | Any | Celery broker + result backend + SSE pub/sub |
| Google Cloud SDK | Latest | For local dev with ADC |

### Local dev setup

1. **Clone the repo** and create a virtual environment.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create `research_environment_api/.env`** — a template of all required variables is in [§22 Environment Variables](#22-environment-variables-reference). A local `.env` file is already gitignored at that path.

4. **Service account credentials:**
   - Set `SERVICE_ACCOUNT_CREDENTIALS_PATH` to the path of a GCP service account JSON key file.
   - The SA needs these roles at minimum: `roles/iam.serviceAccountTokenCreator`, Cloud Identity API access, billing IAM, Cloud Build invoker, Cloud Storage admin.
   - Dev credentials are managed with **sops** (see `credentials/dev/`). To decrypt: `sops -d credentials/dev/credentials.json > /tmp/creds.json`.

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the app:**
   ```bash
   # Flask dev server
   flask --app research_environment_api.wsgi:app run

   # Celery worker + beat (production-like)
   bash celery_endpoint.sh
   ```

7. **Swagger UI** is available at `http://localhost:5000/docs` once the app starts.

### Production (GCP Cloud SQL)

Set `APP_ENV=production`. The app switches from `DATABASE_URL` (plain psycopg2) to Cloud SQL IAM auth using `CLOUD_SQL_INSTANCE_CONNECTION_NAME` + `DATABASE_NAME`. See `modules/db.py:create_cloud_sql_engine`.

---

## 5. Database Models

All models inherit from `ScopedModel` (`modules/model.py`), which provides:
- A UUID primary key `id` (auto-generated via `uuid.uuid4`).
- A `__tablename__` computed from `__table_prefix__ + __local_tablename__`.

There are **four ORM models** across three files:

### 5.1 `WorkbenchActivity` (`modules/monitoring_management/models.py`)

Table: `workbench_workbench_activities`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `invoker_email` | str NOT NULL | Who triggered the workflow |
| `workbench_id` | str NULLABLE | GCE instance name; null during workspace ops |
| `build_type` | `BuildType` enum NOT NULL | e.g. `WORKBENCH_CREATION` |
| `build_status` | `WorkflowStatus` enum NULLABLE | `IN_PROGRESS` / `FAILURE` / `SUCCESS` |
| `workspace_id` | str NOT NULL | GCP project ID of the workspace |
| `build_error_information` | str NULLABLE | Human-readable error from Cloud Build |

This is the **primary audit/workflow-status table**. Every mutating operation (create/destroy/update workbench, create/destroy workspace) writes a row here immediately when the Celery chain is enqueued, then updates `build_status` and optionally `build_error_information` when the Cloud Build job finishes.

### 5.2 `WorkbenchMonitoringData` (`modules/monitoring_management/models.py`)

Table: `workbench_monitoring_data`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_email` | str NOT NULL | |
| `dataset_identifier` | str NULLABLE | Dataset this workbench was created for |
| `instance_type` | `InstanceType` enum NOT NULL | `JUPYTER` / `RSTUDIO` / `COLLABORATIVE` |
| `created_at` | DateTime NOT NULL | When workbench became live |
| `deleted_at` | DateTime NULLABLE | When workbench was stopped/destroyed |
| `workbench_id` | str NULLABLE | GCE instance name |

Used for usage-time reporting (how long each dataset's workbench ran). Populated/closed by background tasks (`add_monitoring_entry`, `mark_monitoring_entry_as_deleted`).

### 5.3 `WorkbenchCollaboratorData` (`modules/workbench_management/models.py`)

Table: `workbench_collaborators`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `workspace_project_id` | str NOT NULL | GCP project ID |
| `service_account_name` | str NOT NULL | Workbench SA name |
| `collaborator_email` | str NOT NULL | Invited user |
| `created_at` | DateTime(timezone=True) | Default: now() |
| `viewed` | Boolean | Default: False — notification acknowledgement flag |
| `status` | `CollaboratorStatus` | `SUCCESS` / `FAILED` / `REMOVED` |

Serves dual purpose: tracks active collaborator memberships and acts as an **in-app notification** system (unviewed `SUCCESS` rows surface as notifications for the collaborator).

### 5.4 `SharingData` (`modules/sharing_management/models.py`)

Table: `sharing_connections`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `sharer_email` | str NOT NULL | Who owns the bucket |
| `accessor_email` | str NOT NULL | Who was granted access |
| `bucket_name` | str NOT NULL | GCS bucket name |
| `project_id` | str NOT NULL | GCP project the bucket lives in |
| `state` | `SharingState` NOT NULL | `SHARED` or `REVOKED` |

Tracks GCS bucket sharing relationships. When access is revoked, the row state flips to `REVOKED` (soft delete).

### 5.5 Alembic migration chain

```
23db34895c85  →  b5d69f2e87da  →  0335c8744390  →  7f6ecf630e82  →  1053e575b4ef  →  f70b6b5a89ae
create_activity  add_sharing_     drop_app_engine  add_sharing_     create_monitor-  create_collabo-
                 statuses         metadata         metadata         ing_table        rators_table
```

To apply all migrations: `alembic upgrade head`. To revert: `alembic downgrade <revision>`.

---

## 6. Core Concepts

### Workspace

A **GCP project** dedicated to a single researcher. Its GCP project ID is derived from the researcher's username: `{username[:15]}-{5 random letters}`. The project is created via Cloud Build (Terraform). A workspace has a billing account attached to it and can contain multiple workbenches.

**Shared Workspace** — a variant where `labels.type=data-sharing` in GCP. Its project ID follows `{username[:15]}-shared-{5 random letters}`. Used specifically for shared storage bucket hosting.

### Workbench

A compute environment running inside a workspace. Three types:

| Type | Backend | Notes |
|---|---|---|
| `JUPYTER` | Google Compute Engine VM | Vertex AI Workbench Jupyter instance |
| `RSTUDIO` | Google Compute Engine VM | RStudio Server with custom TLS certificate |
| `COLLABORATIVE` | Google Compute Engine VM | Shared Jupyter environment for multiple researchers |

A workbench has a lifecycle managed by `WorkbenchStatus`: `CREATING → RUNNING → STOPPING → STOPPED → STARTING → RUNNING → DESTROYING → (deleted)`. Intermediate states (`UPDATING`, `CREATING`, `DESTROYING`, etc.) are derived from in-progress `WorkbenchActivity` rows.

### Cloud Identity

A Google Workspace user account (`username@healthdatanexus.ai`). Created via the Google Admin SDK on behalf of a researcher. Required before any GCP resources can be provisioned — the workspace project is labeled with `cloud_identity_username`.

### Billing Account

A GCP billing account. Researchers need `roles/billing.admin` (owner) or the custom `hdn.shared_billing_account_user` role (shared user) on a billing account before they can create a workspace that links to it.

### Workflow / WorkbenchActivity

The DB representation of a long-running async operation. Every mutation (create/stop/start/update/destroy workbench, create/destroy workspace) creates a `WorkbenchActivity` row immediately with `build_status=IN_PROGRESS`. The Celery chain updates it to `SUCCESS` or `FAILURE` when Cloud Build completes. Clients poll `/workflow/<id>` or stream `/monitoring/events` to observe status changes.

**Workflow ID** = the `WorkbenchActivity.id` UUID.

### EntityScaffolding

A lightweight placeholder returned from list endpoints when a workspace or workbench is currently being provisioned and does not yet have a GCP project to read from. Contains only `id`, `status`, and `gcp_project_id`. Allows the frontend to render a "Creating…" card immediately after the user triggers workspace creation.

### Cloud Identity Group / User Group

A Google Cloud Identity group (`hdn-{name}@healthdatanexus.ai`). Used to grant IAM roles to sets of researchers. Groups are managed through the Cloud Identity API, and their IAM bindings are set on the GCP organization.

### Shared Bucket

A GCS bucket created in a researcher's shared workspace project. Other researchers can be granted `READ_WRITE` (`roles/storage.admin`) or `READ` (`roles/storage.objectViewer`) access. Signed URLs (v4, PUT method) are generated for file upload. Access records are tracked in the `SharingData` table.

### Server-Sent Events (SSE)

The `/monitoring/events` endpoint returns a streaming `text/event-stream` response. The Celery task `set_workflow_status` publishes a JSON message to the Redis channel `workflow_events` when any workflow completes. The SSE endpoint subscribes to that channel and forwards messages to connected clients. Keepalive frames are sent every 30 seconds.

---

## 7. End-to-End Request Flows

### 7.1 Create a Workspace

```
Client                    Flask                     Celery                    Cloud Build
  │                         │                          │                          │
  │ POST /workspace/create  │                          │                          │
  │ {user_email, billing_   │                          │                          │
  │  account_id, user_groups}│                         │                          │
  │────────────────────────>│                          │                          │
  │                         │ @validate_token          │                          │
  │                         │ WorkspaceCreationRequest.load()                     │
  │                         │ WorkspaceCreation entity │                          │
  │                         │   (generates project_id) │                          │
  │                         │                          │                          │
  │                         │ workspace_services.create_workspace(entity)         │
  │                         │ ──────────────────────────────────────────>         │
  │                         │   schedulers.create_workspace()                     │
  │                         │     creates WorkbenchActivity(IN_PROGRESS)          │
  │                         │     builds.create_workspace_build()                 │
  │                         │     workflows.create_workspace() → chain(           │
  │                         │       start_cloud_build,                           │
  │                         │       check_operation_status,                      │
  │                         │       set_workflow_status)                         │
  │                         │                          │ tasks.start_cloud_build  │
  │                         │                          │─────────────────────────>│
  │                         │                          │   Cloud Build Job starts │
  │                         │                          │   (Terraform: create GCP │
  │                         │                          │    project, enable APIs, │
  │                         │                          │    set billing, labels)  │
  │                         │                          │<─────────────────────────│
  │                         │                          │ check_operation_status   │
  │                         │                          │ (polls until done)       │
  │                         │                          │ set_workflow_status      │
  │                         │                          │ → DB: SUCCESS            │
  │                         │                          │ → Redis publish          │
  │                         │                          │   "workflow_events"      │
  │ {workflow_id}           │                          │                          │
  │<────────────────────────│                          │                          │
  │                         │                          │                          │
  │ GET /workflow/{id}      │ (polling)                │                          │
  │────────────────────────>│                          │                          │
  │ {status: "SUCCESS"}     │                          │                          │
  │<────────────────────────│                          │                          │
```

The response to `POST /workspace/create` is a `WorkspaceWorkflowIdentifier` containing the `workflow_id`. The client then polls `/workflow/{workflow_id}` until `status` is `SUCCESS` or `FAILURE`.

### 7.2 Create a Workbench

```
Client                    Flask                     Celery                    GCP
  │                         │                          │                        │
  │ POST /workbench/create  │                          │                        │
  │ {workspace_project_id,  │                          │                        │
  │  user_email, workbench_ │                          │                        │
  │  type, machine_type,    │                          │                        │
  │  dataset_identifier, …} │                          │                        │
  │────────────────────────>│                          │                        │
  │                         │ @validate_token          │                        │
  │                         │ validate_gpu_accelerator()                        │
  │                         │ workspace_services.get_active_google_project()    │
  │                         │   → GCP: list projects (to get numeric_id)        │
  │                         │ WorkbenchCreate entity   │                        │
  │                         │                          │                        │
  │                         │ services.schedule_workbench_create(entity)        │
  │                         │ ──────────────────────────────────>               │
  │                         │   schedulers.create_{type}_workbench()            │
  │                         │     check_workbench_update_quotas()               │
  │                         │       → GCP quota check (cached 24h)              │
  │                         │     creates WorkbenchActivity(IN_PROGRESS)        │
  │                         │     builds.create_{type}_workbench_build()        │
  │                         │     workflows.create_{type}_workbench()           │
  │                         │     → chain(start_cloud_build,                    │
  │                         │             check_operation_status,               │
  │                         │             check_vertex_ai_setup_status [JUPYTER]│
  │                         │             add_monitoring_entry,                 │
  │                         │             assign_initial_collaborators,         │
  │                         │             set_workflow_status)                  │
  │                         │           tasks execute async →────────────────> GCP
  │                         │           Cloud Build runs Terraform              │
  │                         │           GCE/Vertex AI instance created          │
  │                         │           DB: SUCCESS, Redis publish              │
  │ {workflow_id}           │                          │                        │
  │<────────────────────────│                          │                        │
```

### 7.3 SSE Workflow Update

```
Client                    Flask                    Redis
  │                         │                       │
  │ GET /monitoring/events  │                       │
  │ (EventSource)           │                       │
  │────────────────────────>│                       │
  │                         │ services.stream_workflow_events()
  │                         │ SUBSCRIBE workflow_events
  │                         │<──────────────────────│
  │                         │                       │
  │  ─── (Celery task completes somewhere else) ────│
  │                         │ PUBLISH workflow_events│
  │                         │<──────────────────────│
  │ event: workflow_update  │                       │
  │ data: {"workflow_id":…} │                       │
  │<────────────────────────│                       │
  │                         │                       │
  │  ─── (30s with no messages) ────────────────── │
  │ : keepalive             │                       │
  │<────────────────────────│                       │
```

### 7.4 Share a Bucket

```
Client                    Flask                    GCP + DB
  │                         │                        │
  │ POST /sharing/bucket/   │                        │
  │ share                   │                        │
  │ {sharer_email,          │                        │
  │  accessor_email,        │                        │
  │  bucket_name,           │                        │
  │  project_id,            │                        │
  │  permissions}           │                        │
  │────────────────────────>│                        │
  │                         │ @validate_token        │
  │                         │ ShareBucket entity     │
  │                         │ services.share_bucket_to(entity)
  │                         │   _add_iam_permissions() → GCP IAM
  │                         │   SharingData row (state=SHARED) → DB
  │                         │<───────────────────────│
  │ {bucket details}        │                        │
  │<────────────────────────│                        │
```

### 7.5 Admin Bulk-Stop Event Workbenches

```
Browser (admin)           Flask /admin             Celery
  │                         │                        │
  │ POST /admin/events/     │                        │
  │ workbenches/stop        │                        │
  │ Authorization: Basic …  │                        │
  │ {                       │                        │
  │   "workbenches": [      │                        │
  │     {"project_id": …,   │                        │
  │      "workbench_id": …} │                        │
  │   ],                    │                        │
  │   "event_slug": "…"     │                        │
  │ }                       │                        │
  │────────────────────────>│                        │
  │                         │ @validate_admin_page_auth
  │                         │ secrets.compare_digest()
  │                         │ services.stop_event_workbenches()
  │                         │   for each matched workbench:
  │                         │     schedulers.stop_{type}_workbench()
  │                         │       WorkbenchActivity(IN_PROGRESS)
  │                         │       chain() queued ──────────────>
  │ {success: true,         │                        │ (async execution)
  │  message: "Stop         │                        │
  │  initiated for N wb(s)"}│                        │
  │<────────────────────────│                        │
```

---

## 8. API Auth — How Token Validation Works

All public endpoints (everything except `/admin/*`, `/monitoring/events`, and `GET /`) require a valid **Google OIDC ID token** in the `Authorization: Bearer <token>` header.

**`web/decorators.py` — `@validate_token`:**

```python
AUDIENCE = environ.get("CLOUD_RESEARCH_ENVIRONMENTS_API_URL")

def validate_token(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            id_token.verify_oauth2_token(token, google.auth.transport.requests.Request(), AUDIENCE)
        except Exception:
            return {"error": "Unauthorized"}, 401
        return func(*args, **kwargs)
    return decorated
```

- The token must be a valid Google OIDC ID token.
- The `audience` claim in the token must match `CLOUD_RESEARCH_ENVIRONMENTS_API_URL` (the URL at which this API is deployed). This ensures tokens issued for a different service are rejected.
- The decorator does **not** parse claims or inject a user object into the request. Views infer the caller from the request body (`user_email` field) — there is no server-side session.

**`@validate_admin_page_auth`** — used for all `/admin/*` routes. Reads `Authorization: Basic <base64>` and calls `services.authenticate_admin(username, password)`, which uses `secrets.compare_digest` to constant-time compare against `ADMIN_PANEL_USERNAME` / `ADMIN_PANEL_PASSWORD` env vars. Returns `WWW-Authenticate: Basic realm="Admin Panel"` + 401 on failure.

**`/monitoring/events`** — the SSE endpoint has **no token validation**. It performs a manual CORS origin check: if the `Origin` header is not in `CORS_ALLOWED_ORIGINS`, the response sets `Access-Control-Allow-Origin: ""` (empty string). The server always returns HTTP 200 with `text/event-stream` — browsers will block the stream due to the CORS policy, but non-browser clients can connect regardless. There is no 403 response.

---

## 9. URL Routing — Exhaustive Reference

The Flask app registers blueprints in `web/app.py`. Below is the complete route table.

### `GET /` — Healthcheck

| Method | Path | Handler | Auth |
|---|---|---|---|
| GET | `/` | `healthcheck` | None |

Returns `"App available"`, HTTP 200. Used by load balancer health probes.

---

### `/identity` — Cloud Identity Management

| Method | Path | Handler | Auth | Request Body | Response |
|---|---|---|---|---|---|
| POST | `/identity/create` | `create_cloud_identity` | `@validate_token` | `IdentityProvisioningRequest` | `ProvisionedIdentity`, 201 |

**`IdentityProvisioningRequest` fields:** `user_name`, `password`, `recovery_email`, `family_name`, `given_name`.

**Error handlers:** marshmallow `ValidationError` → 422; `CloudIdentityAlreadyConfiguredError` → 409.

---

### `/billing` — Billing Account Management

| Method | Path | Handler | Auth | Notes |
|---|---|---|---|---|
| GET | `/billing/<email>` | `list_billing_accounts` | `@validate_token` + `@cache.cached(300)` | Lists billing accounts for user |
| POST | `/billing/share` | `share_billing_account` | `@validate_token` | Body: `ShareBillingAccountRequest` |
| POST | `/billing/revoke_access` | `revoke_billing_account_access` | `@validate_token` | Body: `RevokeBillingAccountAccessRequest` |

**Error handlers:** marshmallow `ValidationError` → 422.

---

### `/workspace` — Workspace (GCP Project) Management

| Method | Path | Handler | Auth |
|---|---|---|---|
| POST | `/workspace/create` | `create_workspace` | `@validate_token` |
| DELETE | `/workspace/delete` | `delete_workspace` | `@validate_token` |
| GET | `/workspace/<email>` | `list_active_workspaces` | `@validate_token` |
| POST | `/workspace/shared/create` | `create_shared_workspace` | `@validate_token` |
| DELETE | `/workspace/shared/delete` | `delete_shared_workspace` | `@validate_token` |
| GET | `/workspace/shared/<email>` | `list_active_shared_workspaces` | `@validate_token` |
| GET | `/workspace/quotas/<workspace_project_id>` | `list_workspace_quotas` | `@validate_token` |
| POST | `/workspace/update_billing` | `update_workspace_billing_account` | `@validate_token` |
| GET | `/workspace/<email>/<project_id>` | `get_project` | `@validate_token` |

**Schemas:** `WorkspaceCreationRequest` (user_email, billing_account_id, user_groups), `WorkspaceDeletionRequest` (+ workspace_project_id), `SharedWorkspaceCreationRequest`, `SharedWorkspaceDeletionRequest`, `UpdateWorkspaceBillingAccountRequest` (workspace_id, billing_account_id), `ListWorkspaceQuotasRequest` (workspace_project_id only — no region param).

**Response types:** `Workspace` (gcp_project_id, billing_info, workbenches, status, is_owner, service_errors, is_accessible, access_denial_reason), `SimplifiedWorkspace` (gcp_project_id, status, owner, region), `SharedWorkspace` (gcp_project_id, billing_info, **buckets**, status, is_owner, service_errors, is_accessible, access_denial_reason), `EntityScaffolding`, `EntityScaffoldingWorkspaceSchema` (OneOf discriminated union of Workspace | SharedWorkspace | EntityScaffolding).

`GET /workspace/quotas/<workspace_project_id>` queries **all 4 regions** from `constants.AVAILABLE_ZONES` automatically and returns results grouped by region — no region query param is accepted.

---

### `/workbench` — Workbench Lifecycle

| Method | Path | Handler | Auth |
|---|---|---|---|
| POST | `/workbench/create` | `create_workbench` | `@validate_token` |
| PUT | `/workbench/stop` | `stop_workbench` | `@validate_token` |
| PUT | `/workbench/start` | `start_workbench` | `@validate_token` |
| PUT | `/workbench/update` | `update_workbench` | `@validate_token` |
| DELETE | `/workbench/destroy` | `destroy_workbench` | `@validate_token` |
| POST | `/workbench/collaborators` | `add_collaborators` | `@validate_token` |
| DELETE | `/workbench/collaborators` | `remove_collaborators` | `@validate_token` |
| GET | `/workbench/collaborators` | `get_collaborators` | `@validate_token` |
| GET | `/workbench/notifications` | `get_notifications` | `@validate_token` |
| POST | `/workbench/mark-notification-viewed` | `mark_notification_viewed` | `@validate_token` |
| DELETE | `/workbench/notifications` | `clear_all_notifications` | `@validate_token` |
| PUT | `/workbench/renew-ssl-certificate` | `renew_rstudio_ssl_certificate` | `@validate_token` |

**`WorkbenchCreateRequest` fields:** `workbench_type` (JUPYTER/RSTUDIO/COLLABORATIVE), `workspace_project_id`, `user_email`, `dataset_identifier`, `bucket_name`, `machine_type`, `memory`, `cpu`, `disk_size`, `user_groups`, `gpu_accelerator_type`, `sharing_bucket_identifiers`, `collaborators`, `associated_event`, `region`.

**`Workbench` response fields:** `gcp_identifier` (instance name), `status`, `dataset_identifier`, `cpu`, `memory`, `disk_size`, `machine_type`, `url`, `workbench_type`, `zone`, `region`, `sharing_bucket_identifiers`, `collaborators`, `service_account_name`, `workbench_owner_username`, `rstudio_ssl_certificate_expiration_date`.

**`WorkbenchNotification` fields:** `id` (UUID), `email` (collaborator's email), `timestamp`.

---

### `/workflow` — Workflow Status

| Method | Path | Handler | Auth |
|---|---|---|---|
| GET | `/workflow/<workflow_id>` | `get_workflow` | `@validate_token` |
| GET | `/workflow/list/<user_email>` | `list_workflows` | `@validate_token` |

**`Workflow` response fields:** `id`, `build_type`, `status` (mapped from `build_status`), `error` (mapped from `build_error_information`), `workspace_id`.

---

### `/sharing` — Shared Bucket Management

| Method | Path | Handler | Auth |
|---|---|---|---|
| POST | `/sharing/bucket/create` | `create_shared_bucket` | `@validate_token` |
| DELETE | `/sharing/bucket/delete` | `delete_shared_bucket` | `@validate_token` |
| POST | `/sharing/bucket/share` | `share_bucket` | `@validate_token` |
| POST | `/sharing/bucket/revoke_access` | `revoke_access_to_shared_bucket` | `@validate_token` |
| POST | `/sharing/bucket/generate_signed_url` | `generate_signed_url` | `@validate_token` |
| GET | `/sharing/<bucket_name>` | `get_shared_bucket_content` | `@validate_token` |
| POST | `/sharing/bucket/content/create` | `create_shared_bucket_directory` | `@validate_token` |
| DELETE | `/sharing/bucket/content/delete` | `delete_shared_bucket_content` | `@validate_token` |
| GET | `/sharing/<email>/<bucket_name>` | `get_shared_bucket` | `@validate_token` |

**`SharedBucketCreationRequest` validation:** `user_defined_bucket_name` must match `^[a-z0-9-_]{1,32}$`. The actual bucket name is `{user_defined}-{region}-{5 random letters}`.

**`SignedUrlGenerationRequest` validation:** `size` must be `> 0`. Returns a v4 signed PUT URL with `X-Upload-Content-Length` header required on the actual upload request.

**`CreateSharedBucketDirectoryRequest` validation:** `parent_path` must match regex `.*/$|^$` (must end with `/` or be empty string).

---

### `/group` — User Group Management

| Method | Path | Handler | Auth |
|---|---|---|---|
| POST | `/group/create` | `create_group` | `@validate_token` |
| DELETE | `/group/delete` | `delete_group` | `@validate_token` |
| GET | `/group/roles` | `list_roles` | `@validate_token` |
| GET | `/group/roles/iam` | `get_groups_iam_permissions` | `@validate_token` + `@cache.memoize(300s)` |
| GET | `/group/roles/iam/<group_name>` | `get_user_group_iam_roles` | `@validate_token` |
| POST | `/group/roles/add` | `add_roles` | `@validate_token` |
| POST | `/group/roles/remove` | `remove_roles` | `@validate_token` |

Group names are stored and resolved as `hdn-{name}@healthdatanexus.ai` internally. Individual roles are cached with `@cache.memoize(timeout=86400)` at the service level (`get_google_role_entity`).

---

### `/monitoring` — Monitoring and SSE

| Method | Path | Handler | Auth | Notes |
|---|---|---|---|---|
| GET | `/monitoring/datasets` | `list_workbench_monitoring_data_entries` | `@validate_token` | Aggregate usage time per dataset |
| GET | `/monitoring/active_users` | `list_active_users_per_dataset` | `@validate_token` | |
| GET | `/monitoring/events` | `server_side_event` | None (origin check) | `text/event-stream` SSE |

**`WorkbenchMonitoringDataEntry` response fields:** `user_email`, `dataset_identifier`, `instance_type`, `total_time` (human-readable string like "2 Days, 3 Hours, 15 Minutes").

---

### `/admin` — Admin Panel

All routes require HTTP Basic auth (`ADMIN_PANEL_USERNAME` / `ADMIN_PANEL_PASSWORD`). Mix of HTML templates and JSON APIs.

| Method | Path | Handler | Returns |
|---|---|---|---|
| GET | `/admin/` | `admin_home` | HTML (`home.html`) |
| GET | `/admin/celery` | `celery_management` | HTML (`celery_management_home.html`) |
| GET | `/admin/celery-dashboard-data` | `get_celery_dashboard_data` | JSON — task counts + worker stats |
| GET | `/admin/tasks` | `get_tasks` | JSON — `TaskSchema` array. Query params: `q` (name fragment, min 2 chars), `status`, `worker`, `task_type` |
| POST | `/admin/tasks/purge` | `purge_tasks` | JSON `{success, purged_count}` |
| POST | `/admin/tasks/delete` | `delete_tasks` | JSON — `TaskOperationResultSchema` array |
| GET | `/admin/workers` | `get_workers` | JSON — `WorkerStatsSchema` array |
| GET | `/admin/events/workbenches` | `event_workbenches` | HTML |
| GET | `/admin/events/workbenches/data` | `get_workbenches_data` | JSON `{workbenches, errors}` |
| POST | `/admin/events/workbenches/stop` | `stop_event_workbench` | JSON `{success, message}` |
| POST | `/admin/events/workbenches/destroy` | `destroy_event_workbench` | JSON `{success, message}` |
| GET | `/admin/workbench-activities` | `workbench_activities` | HTML |
| GET | `/admin/workbench-activities/data` | `get_workbench_activities_data` | JSON (paginated activities + summary) |
| POST | `/admin/workbench-activities/update-status` | `update_activity_status` | JSON `{success, message}` |

**`WorkbenchActivitiesQueryParams`:** `page`, `per_page`, `q` (search), `status`, `build_type`, `workspace_id`, `workbench_id`, `email`, `sort_by` (validated against allowed values), `sort_direction`.

---

### `/docs` — Swagger UI

Mounted by `flask-swagger-ui`. Reads the spec from `web/static/swagger.json`, which is regenerated from `apispec` on every `create_app()` call. Available at `/docs/`.

---

## 10. View Layer

All views live in `web/{blueprint_name}/views.py`. The pattern is consistent:

```python
@blueprint.route("/create", methods=["POST"])
@validate_token
def create_workspace():
    request_data = schemas.WorkspaceCreationRequest().load(request.json)  # marshmallow
    entity = entities.WorkspaceCreation(**request_data)                   # dataclass
    workflow_id = services.create_workspace(entity)                       # business logic
    return schemas.WorkspaceWorkflowIdentifier().dump({"id": workflow_id}), 201
```

1. **Marshmallow schema** validates and deserializes the request body. `ValidationError` is caught by a blueprint-level error handler and returned as HTTP 422.
2. **Entity/dataclass** encapsulates the validated data and any computed fields (e.g., `workspace_project_id` derived from username + random suffix).
3. **Service function** executes business logic (GCP API calls, DB writes, Celery dispatch).
4. **Marshmallow schema** serializes the response entity.

There are **no HTML templates for end-user views** — only the five admin panel templates in `web/templates/admin_panel/`. The rest of the API is pure JSON, consumed by the React SPA.

---

## 11. Access Control and Decorator Chain

Decorators are stacked in this order on most routes (innermost runs first):

```python
@blueprint.route("/create", methods=["POST"])
@validate_token          # 1st: validates OIDC token against AUDIENCE
@cache.cached(timeout=300)   # optional: response caching
def handler():
    ...
```

For admin routes:
```python
@blueprint.route("/")
@validate_admin_page_auth    # HTTP Basic auth check
def admin_home():
    ...
```

**There is no RBAC or per-user authorization beyond token validation.** Any bearer token holder can call any API endpoint. The assumption is that the calling platform (HDN frontend) enforces who is allowed to manage which resources. The API itself trusts the `user_email` field in the request body as the actor identity.

---

## 12. Background Tasks and Signals

### Celery setup

- **Broker:** Redis (`CELERY_BROKER_URL`)
- **Result backend:** Redis (`CELERY_RESULT_BACKEND`)
- **Serializer:** `pickle` (for task args/results) — tasks pass Python dataclasses and GCP API response objects
- **Task base class:** `WorkflowTask(Task)` — adds `skip_to_last_step()` (skips intermediate chain steps) and `kill_chain()` (terminates and re-triggers with different zone)
- **Auto-retry:** `autoretry_for=(Exception,)`, `max_retries=10`, `retry_backoff=True`

### Celery signal

```python
# background/app.py
@setup_logging.connect
def setup_logging(loglevel, **kwargs):
    # In PRODUCTION: attaches JsonFormatter (outputs JSON lines) to root logger
    # In DEVELOPMENT: attaches plain text formatter
```

This is the only signal handler in the codebase.

### Beat schedule (periodic tasks)

| Task | Schedule            | Purpose |
|---|---------------------|---|
| `export_active_users_per_dataset` | Saturdays 00:00 UTC | Exports CSV of users per dataset → GCS `active_users_per_dataset/` |
| `export_datasets_total_usage_time` | Saturdays 00:00 UTC | Exports CSV of total usage time → GCS `datasets_total_usage_time/` |
| `mark_monitoring_entry_for_stale_workbenches` | Every 6 hours       | Sets `deleted_at` on `WorkbenchMonitoringData` for GCE instances that are stopped |

### Task inventory

All tasks are in `background/tasks.py` and decorated with `@shared_task`.

| Task | `bind` | Key behavior |
|---|---|---|
| `start_cloud_build(build, workbench_activity_id)` | No | Calls Cloud Build API; schedules 30-min fallback `check_and_process_cloud_build_operation` |
| `process_cloud_build_result(operation_context, user_email, workbench_activity_id, fallback_zones, dataset_identifier, collaborators)` | Yes | On failure + recoverable exit code + fallback zones → retries in different zone via `kill_chain()`; else sets `build_error_information` and skips remaining chain steps |
| `set_workflow_status(operation, workbench_activity_id)` | No | Writes final `WorkflowStatus` to DB; publishes `{workflow_id}` to Redis `workflow_events` channel |
| `stop_compute_instance(instance_name, zone, project_id, workbench_activity_id)` | No | Calls GCE stop API |
| `stop_vertex_ai_instance(instance_name, location, project_id, workbench_activity_id)` | No | Calls Vertex AI Notebooks stop API |
| `start_compute_instance(...)` | No | Calls GCE start API |
| `start_vertex_ai_instance(...)` | No | Calls Vertex AI start API |
| `check_vertex_ai_setup_status(passthrough, instance_name, location, project_id, workbench_activity_id)` | Yes | Polls every 30s (`max_retries=None`) until `proxy-url` metadata is present |
| `check_operation_status(operation_context)` | Yes | Polls `Operation.is_done()` until True |
| `check_rstudio_page_status(passthrough, url, workbench_activity_id)` | Yes | Polls HTTPS URL until SSL/TLS is valid |
| `add_monitoring_entry(operation, workbench_activity_id, instance_type, dataset_identifier)` | No | Inserts `WorkbenchMonitoringData` row |
| `mark_monitoring_entry_as_deleted(operation, workbench_activity_id)` | No | Sets `deleted_at = now()` on `WorkbenchMonitoringData` |
| `export_active_users_per_dataset()` | No | Beat task — CSV export |
| `export_datasets_total_usage_time()` | No | Beat task — CSV export |
| `mark_monitoring_entry_for_stale_workbenches()` | No | Beat task — marks stale entries |
| `check_and_process_cloud_build_operation(build_id, workbench_activity_id)` | Yes | 30-min fallback; re-checks Cloud Build and GCE status; handles both workspace and workbench cases |
| `assign_initial_collaborators(operation, collaborators, instance_name, workspace_project_id, user_email)` | No | After collaborative workbench creation, adds each collaborator to the workbench SA IAM |

### Workflow chains

`background/workflows.py` defines a `chain()` for each operation. Example (Jupyter workbench creation):

```python
chain(
    start_cloud_build.s(build, workbench_activity_id),
    check_operation_status.s(),
    check_vertex_ai_setup_status.s(instance_name, location, project_id, workbench_activity_id),
    add_monitoring_entry.s(workbench_activity_id, InstanceType.JUPYTER, dataset_identifier),
    assign_initial_collaborators.s(collaborators, instance_name, workspace_project_id, user_email),
    set_workflow_status.s(workbench_activity_id),
)
```

The `schedulers.py` layer creates the `WorkbenchActivity` DB row and fires the chain:
1. Clears quotas cache for the project.
2. Constructs the `Build` object (via `builds.py`).
3. Creates `WorkbenchActivity` with `build_status=IN_PROGRESS`.
4. Calls `workflows.create_X()` to build the chain.
5. Calls the chain with `()` to enqueue it.

### Zone fallback mechanism

For Jupyter and Collaborative workbenches, if Cloud Build fails with a recoverable error code (zone capacity issue), `process_cloud_build_result` pops the next zone from `fallback_zones`, reconstructs the build substitutions with the new zone, instantiates a fresh workflow chain for that zone, and calls `self.kill_chain()` to terminate the current chain and start the new one.

Available zones per region are in `background/constants.py:AVAILABLE_ZONES` (4 regions × 3 zones).

---

## 13. Email Notifications

**This application sends no emails.**

There are no SMTP, SendGrid, Mailgun, or any other email library imports. There are no email templates.

**In-app notifications** are implemented as `WorkbenchCollaboratorData` rows (table `workbench_collaborators`). When a researcher is added as a collaborator to a workbench:

1. A `WorkbenchCollaboratorData` row is inserted with `status=SUCCESS` or `status=FAILED` and `viewed=False`.
2. The collaborator's client polls `GET /workbench/notifications`, which returns the last 5 unviewed `SUCCESS` rows for their email.
3. `POST /workbench/mark-notification-viewed` sets `viewed=True` for a specific notification.
4. `DELETE /workbench/notifications` clears all notifications for the user.

**Real-time delivery** uses the Redis Pub/Sub + SSE stream at `/monitoring/events` (see [§7.3](#73-sse-workflow-update)).

---

## 14. Entity and Dataclass Types

All business-logic data is exchanged via Python `@dataclass` entities defined in `modules/*/entities.py`. No GCP API objects cross module boundaries.

### Identity Management (`modules/identity_management/entities.py`)

| Dataclass | Fields | Notes |
|---|---|---|
| `CloudIdentityCreation` | `user_name`, `password`, `recovery_email`, `family_name`, `given_name` | `primary_email` computed in `__post_init__` as `{user_name}@{organization_domain}` |

### Billing Management (`modules/billing_management/entities.py`)

| Dataclass | Fields |
|---|---|
| `BillingAccount` | `id`, `name`, `cloud_link`, `is_owner` |

### Workspace Management (`modules/workspace_management/entities.py`)

| Dataclass | Fields | Notes |
|---|---|---|
| `WorkspaceCreation` | `user_email`, `billing_account_id`, `user_groups` | Computes `username`, `workspace_project_id` (`{username[:15]}-{5 random}`), `organization_id` in `__post_init__` |
| `WorkspaceDeletion` | `user_email`, `workspace_project_id`, `billing_account_id` | Computes `username` in `__post_init__` |
| `SharedWorkspaceCreation` | `user_email`, `billing_account_id` | Computes `username`, `workspace_project_id` (`{username[:15]}-shared-{5 random}`) in `__post_init__` |
| `SharedWorkspaceDeletion` | `user_email`, `workspace_project_id`, `billing_account_id` | |
| `WorkspaceListQuery` | `email` | Computes `username` in `__post_init__` |
| `WorkspaceGetQuery` | `workspace_project_id`, `email` | Computes `username` in `__post_init__` |
| `SharedWorkspaceListQuery` | `email` | Computes `username` in `__post_init__` |
| `BillingInfo` | `billing_enabled`, `billing_account_id` | |
| `Workspace` | `gcp_project_id`, `billing_info`, `workbenches`, `status`, `is_owner`, `service_errors`, `is_accessible`, `access_denial_reason` | |
| `SimplifiedWorkspace` | `gcp_project_id`, `status`, `owner`, `region` (optional) | Returned by `GET /workspace/<email>/<project_id>` |
| `SharedWorkspace` | `gcp_project_id`, `is_owner`, `billing_info`, `buckets` (`Iterable[SharedBucket]`), `status`, `service_errors`, `is_accessible`, `access_denial_reason` | Note: has `buckets`, not `workbenches` |
| `EntityScaffolding` | `id`, `status`, `gcp_project_id` | Placeholder for in-progress workspace/workbench creation |

### Workbench Management (`modules/workbench_management/entities.py`)

| Dataclass | Fields | Notes |
|---|---|---|
| `Workbench` | `id`, `resource_id`, `status`, `dataset_identifier`, `cpu`, `memory`, `disk_size`, `type` (`WorkbenchType`), `machine_type`, `region`, `bucket_name`, `vm_image`, `service_account_name`, `brand_name?`, `url?`, `zone?`, `gpu_accelerator_type?`, `workbench_owner_username?`, `rstudio_ssl_certificate_expiration_date?`, `associated_event?`, `sharing_bucket_identifiers` | Built via `from_gce_instance()`. Field is named `type`; the schema serializes it as `workbench_type`. |
| `WorkbenchCreate` | `workbench_type`, `workspace_project_id`, `user_email`, `workspace_numeric_id`, `machine_type`, `memory`, `cpu`, `disk_size`, `region` (**defined twice — see §23**), `dataset_identifier`, `bucket_name`, `user_groups`, `gpu_accelerator_type?`, `sharing_bucket_identifiers`, `collaborators?`, `associated_event?` | `vm_image`, `rstudio_image_url`, `organization_id` computed in `__post_init__` |
| `WorkbenchUpdate` | `workbench_type`, `workspace_project_id`, `user_email`, `machine_type`, `workbench_resource_id` | `organization_id` computed in `__post_init__` |
| `WorkbenchDestroy` | `workbench_type`, `workspace_project_id`, `user_email`, `workbench_resource_id` | |
| `WorkbenchToggleState` | `workbench_type`, `workspace_project_id`, `user_email`, `workbench_resource_id` | Used for both start and stop |
| `WorkbenchRenewSSLCertificate` | `workbench_type`, `workspace_project_id`, `user_email`, `workbench_resource_id` | RStudio only |
| `WorkbenchCollaboratorModification` | `service_account_name`, `workspace_project_id`, `collaborators` | |
| `WorkbenchGetCollaborators` | `workspace_project_id`, `service_account_name` | |
| `WorkbenchGetNotifications` | `workspace_project_id`, `service_account_name` | |
| `WorkbenchClearNotifications` | `workspace_project_id`, `service_account_name` | |

### Sharing Management (`modules/sharing_management/entities.py`)

| Dataclass | Fields | Notes |
|---|---|---|
| `SharedBucketCreation` | `user_defined_bucket_name`, `project_id`, `user_email`, `region` | `bucket_name` = `{user_defined}-{region}-{5 random letters}` |
| `SharedBucketDeletion` | `bucket_name`, `project_id`, `user_email` | |
| `ShareBucket` | `sharer_email`, `accessor_email`, `bucket_name`, `project_id`, `permissions` | `permissions` is `BucketPermissions` enum |
| `SharedBucket` | `bucket_name`, `project_id`, `sharer_email`, `permissions`, `is_admin` | `from_storage_instance()` classmethod |
| `RevokeSharedBucketAccess` | `sharer_email`, `accessor_email`, `bucket_name`, `project_id` | |
| `GenerateSignedUrl` | `bucket_name`, `project_id`, `user_email`, `blob_name`, `size` | v4 signed PUT URL |
| `GetSharedBucketContent` | `bucket_name`, `user_email`, `subdir` | |
| `CreateSharedBucketDirectory` | `bucket_name`, `project_id`, `user_email`, `parent_path`, `directory_name` | `directory_path` = `{parent_path}{directory_name}/` |
| `DeleteSharedBucketContent` | `bucket_name`, `project_id`, `user_email`, `object_name` | Recursive on trailing `/` |
| `SharedBucketObject` | `name`, `size`, `last_modified`, `type` (`BucketObjectType`) | |
| `GetSharedBucket` | `email`, `bucket_name` | |

### Monitoring Management (`modules/monitoring_management/entities.py`)

| Dataclass | Fields |
|---|---|
| `WorkbenchMonitoringDataEntry` | `user_email`, `dataset_identifier`, `instance_type`, `total_time` |
| `UsersPerDataset` | `dataset_identifier`, `user_emails` |
| `QuotaInfo` | `metric_name`, `limit`, `usage`, `region` |
| `BaseQuotaMetricsEntity` | `workspace_project_id` |

### Admin Panel (`modules/admin_panel_management/entities.py`)

| Dataclass | Fields |
|---|---|
| `Task` | `id`, `name`, `args`, `kwargs`, `status`, `worker`, `eta`, `date_done` |
| `TaskResult` | `value`, `error`, `traceback` |
| `TaskOperationResult` | `task_id`, `is_successful` |
| `WorkerStats` | `name`, `stats`, `active_tasks`, `registered_tasks` |

### Common (`modules/common/error_handlers.py`)

| Dataclass | Fields |
|---|---|
| `ServiceError` | `error_type`, `message`, `resource_id`, `service_name`, `details`, `can_retry` |

### Enumerations

| Enum | Values |
|---|---|
| `BuildType` | `WORKSPACE_CREATION`, `WORKSPACE_DELETION`, `SHARED_WORKSPACE_CREATION`, `SHARED_WORKSPACE_DELETION`, `WORKBENCH_CREATION`, `WORKBENCH_STOP`, `WORKBENCH_START`, `WORKBENCH_UPDATE`, `WORKBENCH_DESTROY` |
| `WorkflowStatus` | `IN_PROGRESS`, `FAILURE`, `SUCCESS` |
| `OperationStatus` | `IN_PROGRESS`, `FAILURE`, `SUCCESS` |
| `InstanceType` | `JUPYTER`, `RSTUDIO`, `COLLABORATIVE` |
| `WorkbenchType` | `JUPYTER`, `RSTUDIO`, `COLLABORATIVE` |
| `WorkbenchStatus` | `RUNNING`, `STOPPED`, `STOPPING`, `UPDATING`, `DESTROYING`, `CREATING`, `STARTING` |
| `Region` | `US_CENTRAL`, `NORTHAMERICA_NORTHEAST`, `EUROPE_WEST`, `AUSTRALIA_SOUTHEAST` |
| `BillingAccountRole` | `OWNER`, `SHARED_USER` |
| `IamBillingRole` | `ADMIN` (`roles/billing.admin`), `USER` (custom org role) |
| `IamSharingRole` | `ADMIN` (`roles/storage.admin`), `USER` (`roles/storage.objectViewer`) |
| `SharingState` | `SHARED`, `REVOKED` |
| `BucketPermissions` | `READ_WRITE`, `READ` |
| `BucketObjectType` | `FILE`, `DIRECTORY` |
| `WorkspaceStatus` | `CREATED`, `CREATING`, `DESTROYING` |
| `CollaboratorStatus` | `SUCCESS`, `FAILED`, `REMOVED` |
| `TaskStatus` | `PENDING`, `RECEIVED`, `STARTED`, `SUCCESS`, `FAILURE`, `REVOKED`, `RETRY`, `REJECTED` |
| `GeneralQuotaMetrics` | `IN_USE_IP_ADDRESSES`, `PERSISTENT_DISK_TOTAL`, `VM_INSTANCES`, `CPUS`, `NVIDIA_T4_GPUS` |
| `WorkbenchUpdateQuotaMetricsEntity` | `CPUS` |
| `AppEnv` | `DEVELOPMENT`, `PRODUCTION` |

---

## 15. Admin Console

The admin panel at `/admin/*` is a server-rendered HTML interface secured by HTTP Basic auth. It is NOT part of the public API.

### Templates (`web/templates/admin_panel/`)

| Template | Purpose |
|---|---|
| `admin_panel_base.html` | Bootstrap 4.5.2 base layout; sidebar nav with Dashboard / Celery Management / Events / Entries Management |
| `home.html` | Landing page — jumbotron with "Admin Panel" |
| `celery_management_home.html` | Task queue viewer — active/reserved/scheduled counts, bulk purge/delete, filterable task list |
| `workbench_activities.html` | Paginated, searchable list of `WorkbenchActivity` rows with status update |
| `event_workbenches.html` | Lists all event-associated workbenches; stop/destroy actions |

### Celery task management

- **Purge tasks:** `POST /admin/tasks/purge` — calls `celery_app.control.purge()` to drain queued (not running) tasks.
- **Delete tasks:** `POST /admin/tasks/delete` — 3-step: revoke with SIGKILL, `AsyncResult.forget()`, then `force_task_state(id, "REVOKED")` to ensure the backend reflects the deletion.
- **Inspect:** Worker stats come from `celery_app.control.inspect(timeout=1)` — calls `active()`, `reserved()`, `scheduled()`, `stats()`. Results are cached in-process with a configurable TTL (`ADMIN_PANEL_CACHE_TTL` env var) to avoid hammering the broker.

### Workbench activity filtering

`GET /admin/workbench-activities/data` accepts query params: `page`, `per_page`, `q` (full-text search over workbench_id, email, workspace_id, build_error_information), `status`, `build_type`, `workspace_id`, `workbench_id`, `email`, `sort_by`, `sort_direction`. Implemented in `modules/admin_panel_management/services.py` via SQLAlchemy filter chain.

### Manual status update

`POST /admin/workbench-activities/update-status` accepts `{activity_ids: [uuid, …], new_status: "SUCCESS"|"FAILURE"}`. Used when Cloud Build succeeded but the task chain failed to write the status — allows admin to manually mark activities as resolved without re-running the workflow.

### Dead code: `modules/admin_management/services.py`

This module defines `get_event_workbenches`, `stop_event_workbenches`, and `destroy_event_workbenches`. These are not imported anywhere. The actual implementations used by the admin web layer are in `modules/admin_panel_management/services.py`. The `admin_management` module is dead code.

### Dead code: `start_stopped_workbenches`

`modules/workbench_management/services.py:start_stopped_workbenches(folder_id)` is defined but never called from any view, scheduler, or task. It iterates over `AVAILABLE_ZONES`, restarts Vertex AI instances stopped fewer than 3 days ago. This may be a planned feature that was never wired up.

---

## 16. Fixtures and Seed Data

There are **no fixtures or seed data files** (`fixtures/`, `initial_data.py`, management commands, etc.). The database schema is created entirely by Alembic migrations (`alembic upgrade head`). Test data is created inline within test functions.

Integration tests use `PostgresContainer("postgres:13-alpine")` (Testcontainers) and run Alembic migrations against it on startup — so every integration test run starts from a clean schema.

---

## 17. Error Handling Utilities

### Global Flask error handler (`wsgi.py`)

Registered as `@app.errorhandler(Exception)` — catches everything that escapes blueprint handlers:

```python
if isinstance(error, ValidationError):
    return {"error": f"ValidationError, {error.messages}"}, 400
return {"error": f"{type(error).__name__}, {error.description or str(error)}"}, 500
```

### Blueprint-level error handlers

Each blueprint that can raise known exceptions registers its own handler in `web/{blueprint}/error_handlers.py`:

- **`identity_management`:** `ValidationError` → 422, `CloudIdentityAlreadyConfiguredError` → 409
- **`billing_management`:** `ValidationError` → 422
- **`workspace_management`:** `error_handlers.py` is empty (0 bytes) — relies on global handler
- All others follow the same `ValidationError` → 422 pattern

### `safe_google_service_call` (`modules/common/error_handlers.py`)

A wrapper for GCP API calls that should not crash the request:

```python
result, error = safe_google_service_call(
    func=lambda: gcp_client.some_method(),
    resource_id="projects/my-project",
    service_name="Cloud Resource Manager",
    operation="get project billing info",
)
```

On success: returns `(result, None)`. On any exception: logs it and returns `(default_return, ServiceError(...))`.

`ServiceError` fields: `error_type` (one of `billing_disabled`, `api_not_enabled`, `permission_denied`, `not_found`, `quota_exceeded`, `unknown`), `message` (user-friendly), `resource_id`, `service_name`, `details`, `can_retry`.

This is used heavily in `workspace_management/services.py` when building the `Workspace` response — each GCP call that might fail appends to `service_errors` rather than crashing the whole list response.

### `QuotaExceededError` (`modules/monitoring_management/exceptions.py`)

Raised by `check_workbench_update_quotas()` when a workbench update would exceed GCP quota. Has a `description` field with a human-readable message. Caught by the global error handler and returned as HTTP 500 (this could be improved to 422/409 — see §21).

---

## 18. External Integrations and Services

### Google Cloud Build

**Purpose:** All GCP resource provisioning. Cloud Build runs Terraform steps from a sibling infrastructure repository.

**How:** `build_templates.py` defines Cloud Build step lists. `builds.py` assembles `cloudbuild_v1.Build` objects with substitution variables (project IDs, machine types, region, etc.). `tasks.start_cloud_build` calls `google_cloud_build_client.create_build(project_id=PROJECT_ID, build=build)`.

**Terraform repo:** Cloned during Cloud Build via a GitHub SSH key stored in Secret Manager. Steps reference paths like `terraform-workbench-creation/workbench/jupyter/`.

**Error codes:** `CLOUD_BUILD_ERROR_MESSAGE` in `constants.py` maps exit codes {3, 7, 14, 40, 43, 44, 50} to user-friendly messages. Other codes are treated as non-recoverable failures.

### Google Compute Engine

**Purpose:** Hosting Jupyter/RStudio/Collaborative workbench VMs.

**How:** GCE is used for reading instance state (`google_compute_engine_instances_client.aggregated_list`), stopping/starting instances (`stop`/`start` API), and checking operation status (`google_zone_operations_client.get`). VMs are **created** by Cloud Build/Terraform, not directly.

**Accelerator validation:** For GPU workbenches, `services.validate_gpu_accelerator` checks against either a static `AcceleratorConfig.AcceleratorType` enum (Jupyter/Collaborative) or a live `aggregated_list` call (RStudio).

### Vertex AI Notebooks (Workbench Instances API)

**Purpose:** Used for Jupyter instance stop/start via the Notebooks API (separate from GCE stop/start).

**How:** `google_cloud_notebooks_client.stop_instance / start_instance`. Operation status polled via `google_cloud_notebooks_operation_client.get_operation`.

### Google Cloud Storage

**Purpose:** Shared research buckets + weekly CSV exports.

**How:** Direct SDK calls (`google_cloud_storage_client`). CORS is configured on bucket creation (`PUT` + `OPTIONS` allowed). Signed URLs are v4, PUT method only, requiring `X-Upload-Content-Length` header. Blobs are listed with `delimiter="/"` to simulate directory structure.

`sharing_management.services.specify_buckets_fusing_permissions(bucket_list, caller_email)` is called by `schedulers.py` during workbench creation — it takes the `sharing_bucket_identifiers` list from the creation request and attaches the appropriate IAM bindings on each bucket for the new workbench's service account.

### Google Cloud Identity / Google Workspace Admin SDK

**Purpose:** Creating researcher Google accounts + group management.

**How:**
- `WorkspaceClient` in `library/google/workspace.py` wraps the Admin Directory API v1 (`users().insert`) and Cloud Identity API v1 (`groups().memberships().create`).
- Domain delegation is required: the service account must be granted G Suite domain-wide delegation with the appropriate OAuth scopes.
- `library/google/delegation.py:domain_delegate_credentials(credentials, user_email, scopes)` delegates to `user_email` before making admin calls.

### Google Cloud Billing API

**Purpose:** Listing and managing billing account IAM (who has access to which billing account).

**How:** `library/google/billing.py:BillingClient` wraps the Cloud Billing API using delegated credentials. `IamBillingRole.USER` is a **hard-coded custom role** at `organizations/3105849901/roles/hdn.shared_billing_account_user` — this production org ID is baked into source code.

### Google Cloud Resource Manager

**Purpose:** Creating/listing/deleting GCP projects (workspaces).

**How:** `google_cloud_resource_client` (ProjectsClient) is used to list active projects by label filters: `labels.cloud_identity_username:{u} lifecycleState:ACTIVE parent.id:{workbenches_parent_project_id}`.

### Google IAM

**Purpose:** Managing service account IAM bindings for workbench collaborators.

**How:** `google_iam_client` + helpers in `workbench_management/utils.py` — `add_iam_binding` and `remove_iam_binding` patch the SA IAM policy.

### Google Secret Manager

**Purpose:** Storing the GitHub SSH key used by Cloud Build to clone the Terraform repo, and the RStudio TLS certificate JSON.

**How:** `google_secret_manager_client.access_secret_version(...)` in `builds.py:_fetch_rstudio_certificate`.

### Google Service Usage / Cloud Monitoring

**Purpose:** Quota checking before workbench creation/update.

**How:** `check_google_quotas()` in `modules/monitoring_management/services.py` queries the Service Usage API for quota limits and the Cloud Monitoring Metric Service for current usage. Results are memoized via `@cache.memoize(QUOTAS_CACHE_TIMEOUT=86400)`. Cache is cleared by `clear_quotas_cache()` before every workbench creation/update (in `schedulers.py`).

### Redis

**Purpose:** Celery broker, Celery result backend, and SSE pub/sub channel.

**How:** A `redis.StrictRedis` client is built from `CELERY_BROKER_URL` and stored on `app.config.redis_client`. `set_workflow_status` publishes to channel `"workflow_events"`; `stream_workflow_events()` subscribes and yields SSE frames.

---

## 19. Testing Approach

### Test types

| Type | Location | Marker | Runs against |
|---|---|---|---|
| Unit | `tests/unit/` | `@pytest.mark.unit` | Mocked GCP + SQLAlchemy |
| Integration | `tests/integration/` | `@pytest.mark.integration` | Real Postgres (Testcontainers) + fake GCS |

### Unit tests

Fixtures in `tests/unit/conftest.py`:
- `mock_config` — patches `create_config` entirely; GCP clients are MagicMocks.
- `setup_app_config` (autouse) — applies mock_config before each test.
- `app` — patches `create_sql_engine` and `create_cloud_sql_engine` to use SQLite in-memory.
- `client` — Flask test client.
- `mock_db_session` — patches `app.database_session()` to return a mock.

**`generate_required_maps` is monkey-patched at the top of `conftest.py`** before any app import — this prevents the live GCE `MachineTypesClient.aggregated_list` call that happens at module import time in `workbench_management/utils.py`.

Unit test coverage:
- `unit/background/test_builds.py` — Cloud Build substitution assertions
- `unit/background/test_operations.py` — Operation status mappings
- `unit/background/test_schedulers.py` — DB row creation + chain invocation
- `unit/background/test_tasks.py` — Cloud Build result task (success/failure/retry)
- `unit/services/test_billing_services.py`
- `unit/services/test_identity_services.py`
- `unit/services/test_monitoring_services.py` — interval time calculations
- `unit/services/test_sharing_services.py`
- `unit/services/test_user_group_services.py`

### Integration tests

Fixtures in `tests/integration/conftest.py`:
- `postgres_container` (session) — `PostgresContainer("postgres:13-alpine", driver="psycopg2")`.
- `gcs_emulator_container` (session) — `fsouza/fake-gcs-server:latest` on port 4443, running in HTTP mode.
- `db_engine` (session) — creates engine + `alembic upgrade head`.
- `fake_gcs_client` (session) — GCS client pointed at the emulator.
- `mock_gcp_environment` — patches `google.cloud.storage.Client` to use the emulator.
- `app` — patches engine creators to use the test Postgres.
- `client` — Flask test client.
- `db_session` — per-test connection with rollback for isolation.
- `celery_eager_config` + `celery_eager` — sets `task_always_eager=True` so Celery tasks run synchronously in-process; uses an independent DB session to avoid nested transaction conflicts.
- `mock_workspace_services` — patches `get_active_google_project` to return a fixed `SimplifiedWorkspace` without hitting GCP.

**`validate_token` is patched globally** in integration tests to `side_effect=lambda f: f` (pass-through), so all endpoints are auth-free.

**`service_account.Credentials.from_service_account_file`** is patched to return `AnonymousCredentials` — no real GCP calls are made except against the emulated GCS server.

Integration test files:
- `integration/monitoring/test_monitoring_api_integration.py` (11 tests)
- `integration/sharing/test_sharing_api_integration.py` (14 tests)
- `integration/workbench/test_workbench_api_workflow_integration.py` (10 tests)
- `integration/workbench/test_workbench_collaborators_integration.py` (8 tests)
- `integration/workflow/test_workflow_api_integration.py` (9 tests)
- `integration/workspace/test_workspace_api_integration.py` (12 tests)

### Running tests

```bash
# All tests
make test

# Unit only
make test-unit

# Integration only
make test-integration

# Specific suites
make test-integration-sharing
make test-integration-workbench
make test-integration-workspace
make test-integration-monitoring
make test-integration-workflow

# Coverage report (terminal)
make coverage

# Coverage HTML
make coverage-html   # opens htmlcov/index.html
```

### Testing guide

See `docs/testing.md` for a 146-line guide covering Testcontainers setup, fake GCS server quirks, and the `celery_eager` fixture pattern.

---

## 20. CI/CD

Three GitHub Actions workflows in `.github/workflows/`:

### `black.yml`

Runs on every push. Checks code formatting with `black --check --verbose .`. Fails if any file is not formatted. Python 3.11, `pip install -r requirements.txt`.

### `unit-tests.yml`

Runs on every push. `make test-unit`. Python 3.11, pip cache keyed by `requirements.txt` hash.

### `integration-tests.yml`

Runs on every push. `make test-integration`. Same setup + `TESTCONTAINERS_RYUK_DISABLED=true` (required for GitHub Actions runners where Ryuk's Docker socket access is restricted).

### Production deployment

The `Dockerfile` produces the production image:
- Base: `python:3.11-slim`
- Entry: `gunicorn research_environment_api.wsgi:app`
- Workers: `GUNICORN_WORKERS` (default 3) × threads: `GUNICORN_THREADS` (default 8)
- Timeout: `--timeout 0` (disabled — long-running SSE connections would otherwise get killed)

Celery workers are started separately via `celery_endpoint.sh`:
```bash
python -m http.server 8080 &          # health check endpoint for worker container
celery -A research_environment_api.worker beat &    # periodic tasks
celery -A research_environment_api.worker worker    # task execution
```

---

## 21. Common Failure Modes

### Token audience mismatch

**Symptom:** All API calls return 401.

**Cause:** `CLOUD_RESEARCH_ENVIRONMENTS_API_URL` env var on the server does not match the `audience` claim in the client's OIDC token. The token was issued for a different URL.

**Fix:** Ensure `CLOUD_RESEARCH_ENVIRONMENTS_API_URL` matches the URL the client requested tokens for. In dev: set it to `http://localhost:5000`.

---

### Cloud Build job fails silently

**Symptom:** `WorkbenchActivity` row stays in `IN_PROGRESS` indefinitely after a network hiccup.

**Cause:** The Celery task chain crashed before `set_workflow_status` ran (e.g., broker restart, worker killed).

**Fix:** Use the admin panel `/admin/workbench-activities` to manually set the activity to `FAILURE`. Then re-trigger the operation from the UI.

**Prevention:** The `check_and_process_cloud_build_operation` fallback task is scheduled 30 minutes after `start_cloud_build` to recover from this exact scenario.

---

### Quota check fails to raise correct HTTP status

**Symptom:** `QuotaExceededError` from workbench update returns HTTP 500 instead of a meaningful 4xx.

**Cause:** `QuotaExceededError` is not caught by any blueprint handler — it falls through to the global `@app.errorhandler(Exception)` which maps it to 500.

**Fix:** Add a blueprint-level handler for `QuotaExceededError` → 422 in `web/workbench_management/`. (This is a known gap.)

---

### GCE machine type map fails to initialize

**Symptom:** Import error / crash on startup: `generate_required_maps` raises an exception.

**Cause:** `workbench_management/utils.py` calls `MachineTypesClient.aggregated_list` at **module import time**. If GCP credentials are missing or invalid, the import fails.

**Fix:** Ensure `SERVICE_ACCOUNT_CREDENTIALS_PATH` points to a valid SA key file before starting the app. In tests, `generate_required_maps` is monkey-patched before any import.

---

### Admin panel inspector returns empty data

**Symptom:** `/admin/celery-dashboard-data` returns zeros for all counts even though tasks are running.

**Cause:** Celery inspect has a 1-second timeout. If the broker is slow or the worker hasn't responded in time, the result is empty. The cached result may also be stale (`ADMIN_PANEL_CACHE_TTL`).

**Fix:** Check Redis connectivity. The in-process cache (`admin_panel_management/cache.py`) can be bypassed by restarting the Flask process.

---

### `workspace-controller-repo/` references

**Symptom:** Confusion about which component handles GCP operations.

**Clarification:** The `workspace-controller-dev-*.json` credential files and any `workspace-controller-repo/` directory are historical artifacts from a previous architecture. They are no longer used. All GCP operations go through Cloud Build triggered by this Flask service.

---

### Credential JSON files checked into repo

`credentials-api.json`, `credentials-api-prod.json`, `research-environment-api-dev-*.json`, and `workspace-controller-dev-*.json` are service account keys committed directly to the repository. This is a security concern — if these are active keys, they should be rotated and moved to a secrets manager. The preferred approach is sops-encrypted files in `credentials/dev/` and `credentials/prod/`.

---

### Celery `pickle` serializer

The Celery configuration uses `task_serializer = "pickle"`, `result_serializer = "pickle"`, and `accept_content = ["application/json", "application/x-python-serialize", "pickle"]`. This allows Python dataclasses and GCP API response objects to be passed between tasks without explicit JSON serialization. However, **pickle deserialization of untrusted data is a security risk** — the Redis broker should be access-controlled.

---

## 22. Environment Variables Reference

All variables are read in `modules/config.py`. Required unless marked optional.

### Core application

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Set to `production` to enable Cloud SQL + JSON logging |
| `CLOUD_RESEARCH_ENVIRONMENTS_API_URL` | — | This service's own public URL — used as the OIDC token audience |
| `SERVICE_ACCOUNT_CREDENTIALS_PATH` | — | Path to GCP service account JSON key file |
| `PROJECT_ID` | — | GCP project ID where Cloud Build runs |
| `ORGANIZATION_ID` | — | GCP organization ID |
| `CUSTOMER_ID` | — | Google Workspace customer ID |
| `ORGANIZATION_DOMAIN` | `healthdatanexus.ai` | Google Workspace domain |

### Database

| Variable | Used when | Description |
|---|---|---|
| `DATABASE_URL` | `APP_ENV=development` | Full PostgreSQL URL (`postgresql://user:pass@host/db`) |
| `DATABASE_NAME` | `APP_ENV=production` | Cloud SQL database name |
| `CLOUD_SQL_INSTANCE_CONNECTION_NAME` | `APP_ENV=production` | Cloud SQL instance connection string |

### Celery / Redis

| Variable | Description |
|---|---|
| `CELERY_BROKER_URL` | Redis URL (also used for SSE pub/sub) |
| `CELERY_RESULT_BACKEND` | Redis URL for task results |

### Caching

| Variable | Description |
|---|---|
| `CACHE_TYPE` | Flask-Caching backend (e.g., `SimpleCache`, `RedisCache`) |

### GCP infrastructure

| Variable | Description |
|---|---|
| `BILLING_ACCOUNT_CREATOR_GROUP_ID` | Cloud Identity group ID; new researcher accounts are added here |
| `VPC_SECURE_PERIMETER_NAME` | VPC Service Controls perimeter name |
| `TERRAFORM_BRANCH_NAME` | Git branch to clone in Cloud Build (e.g., `main`) |
| `TERRAFORM_REPO_NAME` | GitHub repo name for Terraform |
| `CLOUD_BUILD_SERVICE_ACCOUNT_NAME` | SA email for Cloud Build jobs |
| `DATA_PROJECT_NAME` | GCP project containing datasets |
| `NETWORK_NAME` | VPC network name for workbench VMs |
| `WORKBENCHES_PARENT_PROJECT_ID` | GCP folder/project ID that workspace projects are created under |
| `SHARING_FOLDER_ID` | GCP folder ID for shared workspace projects |

### Workbench-specific

| Variable | Description |
|---|---|
| `JUPYTER_STARTUP_SCRIPT` | GCS path to Jupyter startup script (e.g., `gs://bucket/script.sh`) |
| `RSTUDIO_STARTUP_SCRIPT` | GCS path to RStudio startup script |
| `RSTUDIO_IMAGE_URL` | Container image URL for RStudio VMs |
| `RSTUDIO_DNS_PROJECT` | GCP project hosting the RStudio DNS zone |
| `RSTUDIO_DNS_ZONE` | Cloud DNS zone name for RStudio domains |
| `RSTUDIO_DOMAIN_NAME` | Base domain for RStudio URLs |
| `RSTUDIO_CERTIFICATE_SECRET_ID` | Secret Manager secret ID for RStudio TLS cert JSON |
| `GITHUB_SSH_KEY_KSM_ID` | Secret Manager secret ID for GitHub SSH key |
| `GCP_CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins (default: `http://localhost:3000`) |
| `GCP_SIGNED_URL_EXPIRATION_TIME` | Signed URL TTL in seconds |

### Monitoring / exports

| Variable | Description |
|---|---|
| `MONITORING_CSV_EXPORTS_ROOT_BUCKET` | GCS bucket for weekly CSV exports |

### Admin panel

| Variable | Description |
|---|---|
| `ADMIN_PANEL_USERNAME` | HTTP Basic auth username |
| `ADMIN_PANEL_PASSWORD` | HTTP Basic auth password |
| `ADMIN_PANEL_CACHE_TTL` | Celery inspector cache TTL in seconds |

### Example local `.env`

```bash
APP_ENV=development
DATABASE_URL=postgresql://postgres:password@localhost:5432/research_env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CACHE_TYPE=SimpleCache
CLOUD_RESEARCH_ENVIRONMENTS_API_URL=http://localhost:5000
SERVICE_ACCOUNT_CREDENTIALS_PATH=/path/to/service-account.json
PROJECT_ID=my-gcp-project
ORGANIZATION_ID=123456789
CUSTOMER_ID=C0abc1234
BILLING_ACCOUNT_CREATOR_GROUP_ID=00000000000000000000
VPC_SECURE_PERIMETER_NAME=my-perimeter
TERRAFORM_BRANCH_NAME=main
TERRAFORM_REPO_NAME=infrastructure
JUPYTER_STARTUP_SCRIPT=gs://my-bucket/startup.sh
RSTUDIO_STARTUP_SCRIPT=gs://my-bucket/rstudio-startup.sh
CLOUD_BUILD_SERVICE_ACCOUNT_NAME=cloudbuild@my-project.iam.gserviceaccount.com
RSTUDIO_IMAGE_URL=gcr.io/my-project/rstudio:latest
DATA_PROJECT_NAME=data-project
NETWORK_NAME=default
RSTUDIO_DNS_PROJECT=dns-project
RSTUDIO_DNS_ZONE=my-zone
RSTUDIO_DOMAIN_NAME=rstudio.healthdatanexus.ai
RSTUDIO_CERTIFICATE_SECRET_ID=rstudio-cert
SHARING_FOLDER_ID=folders/123456789
WORKBENCHES_PARENT_PROJECT_ID=folders/987654321
GCP_SIGNED_URL_EXPIRATION_TIME=3600
GCP_CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.healthdatanexus.ai
GITHUB_SSH_KEY_KSM_ID=github-ssh-key
MONITORING_CSV_EXPORTS_ROOT_BUCKET=my-monitoring-exports-bucket
ADMIN_PANEL_USERNAME=admin
ADMIN_PANEL_PASSWORD=changeme
ADMIN_PANEL_CACHE_TTL=60
```

---

## 23. Known Bugs

### Reported duplicate function definitions (`get_simplified_workspace`, `get_shared_bucket`)

**Reported:** Duplicate definitions of `get_simplified_workspace` and `get_shared_bucket` at the bottom of some module file.

**Current state (as of this writing):** An AST-based scan of every `.py` file in this repo found no duplicate definitions of either name. `get_shared_bucket` exists exactly once (`web/sharing_management/views.py:274`). `get_simplified_workspace` does not exist under that name — the nearest equivalent is `get_project` in `web/workspace_management/views.py:316`, which calls `services.get_project()` and serializes the result with `schemas.SimplifiedWorkspace()`. These duplicates may have already been cleaned up. To check: `grep -rn "def get_simplified_workspace\|def get_shared_bucket" research_environment_api/`

---

### `modules/admin_management/services.py` is dead code

`modules/admin_management/services.py` duplicates `get_event_workbenches`, `stop_event_workbenches`, and `destroy_event_workbenches` from `modules/admin_panel_management/services.py`. The admin web layer imports from `admin_panel_management`, not `admin_management`. The module is never imported anywhere.

---

### `QuotaExceededError` returns HTTP 500

When a workbench update is rejected due to quota limits, the error propagates to the global error handler and returns HTTP 500. It should return HTTP 422 or 409 with the quota-exceeded message. No blueprint-level handler catches it.

---

### `WorkbenchCreate` has `region` field defined twice

In `modules/workbench_management/entities.py`, the `WorkbenchCreate` dataclass defines `region: Region` on **two separate lines** (lines 192 and 195), with `dataset_identifier` and `bucket_name` sandwiched between them. Python silently accepts this — the second definition wins — but it is confusing to read and may mask an ordering bug in the dataclass field sequence. The field `region` appears twice in the class body; only one survives in `__init__`.

---

### Duplicate `generate_resource_name_from_dataset_identifier`

The function `generate_resource_name_from_dataset_identifier(dataset_identifier)` is defined independently in both `modules/workbench_management/services.py:237` and `modules/workspace_management/services.py:422`. The schedulers import from `workbench_management`. The copy in `workspace_management` is never called — it is dead code.

---

### Hard-coded organization ID in billing client

`library/google/billing.py` hard-codes the GCP organization ID and a custom IAM role name:

```python
IamBillingRole.USER = "organizations/3105849901/roles/hdn.shared_billing_account_user"
```

This makes the billing client non-portable and means changes to the org ID or role name require a code change.

---

### `@dataclass` applied to `StrEnum` subclasses

In `modules/monitoring_management/entities.py`, `GeneralQuotaMetrics` and `WorkbenchUpdateQuotaMetricsEntity` are decorated with both `@dataclass` and inherit from `StrEnum`. The `@dataclass` decorator is effectively a no-op on an enum — it doesn't add `__init__` or `__repr__` because `enum.EnumMeta` takes precedence. The decorator is harmless but misleading.

---

## 24. Glossary

| Term | Definition |
|---|---|
| **Workspace** | A GCP project dedicated to a single researcher, created via Terraform through Cloud Build. The core unit of isolation. |
| **Shared Workspace** | A GCP project variant (`labels.type=data-sharing`) used to host shared storage buckets. |
| **Workbench** | A compute environment (VM) running inside a workspace. Types: Jupyter, RStudio, Collaborative. |
| **Cloud Identity** | A Google Workspace user account (`@healthdatanexus.ai`). Required before any GCP resources can be provisioned. |
| **Billing Account** | A GCP billing account. Researchers must have access to one before creating a workspace. |
| **Workflow** | A long-running async operation tracked by a `WorkbenchActivity` DB row. Identified by a UUID. |
| **WorkbenchActivity** | DB row in `workbench_workbench_activities`. Tracks every mutating GCP operation from `IN_PROGRESS` to `SUCCESS`/`FAILURE`. |
| **EntityScaffolding** | A lightweight placeholder object returned during workspace/workbench creation to indicate "in progress" before the GCP resource exists. |
| **Cloud Build** | Google Cloud's CI/CD execution environment. Used here to run Terraform steps for all GCP resource provisioning. |
| **SSE** | Server-Sent Events. The `/monitoring/events` endpoint streams `text/event-stream` messages to clients using Redis Pub/Sub as the message bus. |
| **Notification** | An unviewed `WorkbenchCollaboratorData` row with `status=SUCCESS`. Surfaced via `/workbench/notifications`. No emails are sent. |
| **Shared Bucket** | A GCS bucket hosted in a shared workspace, with granular IAM access given to other researchers. |
| **Signed URL** | A time-limited v4 GCS URL (PUT method) for direct browser-to-GCS file upload, bypassing this API. |
| **User Group** | A Cloud Identity group (`hdn-{name}@healthdatanexus.ai`). Used to grant IAM roles to sets of researchers. |
| **safe_google_service_call** | A utility wrapper that catches GCP API exceptions and returns a `(result, ServiceError | None)` tuple, allowing partial responses instead of hard failures. |
| **WorkflowTask** | Custom Celery `Task` subclass that adds `skip_to_last_step()` (jump to the final chain step) and `kill_chain()` (terminate and re-trigger in a different zone) for zone-fallback logic. |
| **Zone fallback** | When Cloud Build fails with a recoverable error code (GCE zone capacity), the task chain terminates, picks the next available zone from `AVAILABLE_ZONES`, and starts a fresh chain for that zone. |
| **Beat** | Celery Beat — the scheduler that triggers periodic tasks (`export-active-users-per-dataset-weekly`, `mark-stale-workbenches-every-six-hours`, etc.). |
| **Flower** | Celery monitoring UI, started via `flower_endpoint.sh` at `/flower`. Not required for production. |
| **sops** | Mozilla sops — used to encrypt/decrypt credential files in `credentials/dev/` and `credentials/prod/`. |
| **HDN** | Health Data Nexus — the platform this service is part of. |
| **ScopedModel** | SQLAlchemy `DeclarativeBase` subclass that provides `id: UUID PK` and a `__tablename__` computed from class-level prefix constants. |
| **apispec** | Library used to auto-generate the OpenAPI 3.0 spec at startup from Flask routes + Marshmallow schemas. Output: `web/static/swagger.json`. |
| **pickle serializer** | Celery is configured to use Python's `pickle` format for task arguments and results, enabling dataclasses and GCP objects to pass between tasks without custom serialization. |