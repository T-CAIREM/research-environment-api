# Research Environment API

The Research Environment API is the backend service behind the
[HealthDataNexus](https://healthdatanexus.ai) platform. It provisions and
manages cloud-based research environments ("workbenches") on Google Cloud
Platform, along with the projects, identities, billing, data sharing, and
monitoring that surround them.

It is a Flask HTTP API backed by Celery workers. Long-running provisioning work
is dispatched to workers, which orchestrate it by triggering Google Cloud Build
pipelines that run Terraform.

## Architecture

- **Web API (Flask + Gunicorn)** — HTTP endpoints, request validation
  (Marshmallow), and auto-generated OpenAPI docs.
- **Background workers (Celery + Redis)** — run long operations (workbench and
  workspace provisioning, billing setup, data sharing) asynchronously. Flower
  provides task monitoring.
- **Provisioning (Cloud Build + Terraform)** — workers assemble Cloud Build
  pipelines that clone the workbench-provisioning Terraform repo and run
  `terraform apply` to create per-researcher environments.
- **Persistence (PostgreSQL / Cloud SQL)** — application state via SQLAlchemy,
  schema managed with Alembic. On GCP, connections use the Cloud SQL Python
  Connector.
- **Google Cloud integration** — extensive use of GCP client libraries
  (Resource Manager, Compute, Notebooks, Billing, IAM, Secret Manager, Storage,
  Monitoring, Cloud Identity).

## API

Endpoints are grouped into Flask blueprints. Interactive OpenAPI documentation
is served at `/docs` (Swagger UI).

| Prefix | Area |
|--------|------|
| `/identity` | User identity management |
| `/group` | User group management |
| `/billing` | Billing accounts and budgets |
| `/workspace` | Researcher workspace (project) management |
| `/workbench` | Jupyter / RStudio workbench lifecycle |
| `/workflow` | Long-running workflow status, including live events |
| `/sharing` | Data and bucket sharing |
| `/monitoring` | Usage monitoring and CSV exports |
| `/admin` | Admin panel operations |
| `/` | Health check (`GET /` → `200 App available`) |
| `/docs` | Swagger UI |

## Tech stack

Python 3.11 · Flask · Gunicorn · Celery + Redis (+ Flower) · SQLAlchemy +
Alembic · PostgreSQL / Cloud SQL · Marshmallow + apispec + flask-swagger-ui ·
Google Cloud client libraries · Terraform (run via Cloud Build).

## Repository layout

```
research_environment_api/
  web/         Flask blueprints (HTTP layer) + OpenAPI/Swagger
  modules/     Domain logic (workbench, workspace, billing, identity, ...)
  background/  Celery tasks and Cloud Build / Terraform pipeline templates
  library/     Google Cloud client wrappers
  tests/       Unit and integration tests
alembic/       Database migrations
```

## Prerequisites

- Python 3.11
- PostgreSQL and Redis (for local development)
- Access to a Google Cloud project with the required APIs enabled

## Configuration

All runtime configuration is supplied through environment variables. Copy the
template and fill in values for your environment:

```commandline
cp .env.example .env
```

See `.env.example` for the full list of variables and which are required. `.env`
is gitignored and must never be committed.

## Local development

Create a virtual environment and install dependencies:

```commandline
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Apply database migrations (see [Database](#database)), then run the API:

```commandline
flask run
```

Run the Celery worker and beat scheduler (or use `./celery_endpoint.sh`):

```commandline
celery -A research_environment_api.worker worker --loglevel=info
celery -A research_environment_api.worker beat   --loglevel=info
```

Optionally monitor tasks with Flower (or use `./flower_endpoint.sh`):

```commandline
celery -A research_environment_api.worker flower
```

## Database

The schema is managed with Alembic:

```commandline
alembic upgrade head                              # apply all migrations
alembic revision --autogenerate -m "description"  # create a new migration
```

## Running the tests

`make help` lists the available targets. Common ones:

```commandline
make test-unit          # all unit tests
make test-integration   # all integration tests (uses testcontainers)
make test               # unit + integration
```

See `docs/testing.md` for details on the test suite and its infrastructure.

## License

This project is licensed under the BSD 3-Clause License — see [LICENSE](LICENSE).
