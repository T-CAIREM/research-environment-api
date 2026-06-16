# Research Environment API

The Research Environment API is the backend service that provisions and manages
cloud-based research environments ("workbenches") on Google Cloud Platform. It
exposes a Flask HTTP API backed by Celery workers and orchestrates workbench
creation by triggering Cloud Build pipelines that run Terraform.

## Requirements

- Python 3.11
- PostgreSQL and Redis (for local development)
- A Google Cloud project and a service-account key with the required IAM roles
- [SOPS](https://github.com/getsops/sops) for credential management

## Configuration

All runtime configuration is supplied through environment variables. Copy the
template and fill in values for your environment:

```commandline
cp .env.example .env
```

See `.env.example` for the full list of variables and which are required. `.env`
is gitignored and must never be committed.

## Running the tests

`make help` lists the available targets. Common ones:

```commandline
make test-unit          # all unit tests
make test-integration   # all integration tests (uses testcontainers)
make test               # unit + integration
```

See `docs/testing.md` for details on the test suite and its infrastructure.

## Bootstrapping a Cloud SQL database

### Permissions

In order for the app's user to have access to the newly created database, the
following permissions need to be present:

```GRANT ALL ON SCHEMA public TO username```

## Credentials

The service authenticates to Google Cloud using a service-account key. Set
`SERVICE_ACCOUNT_CREDENTIALS_PATH` (see `.env.example`) to the path of that key
file. Provision and distribute the credential through your own secret-management
workflow — it is never stored in this repository.
