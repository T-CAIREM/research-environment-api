# Testing Guide

This document describes the test suite for the Research Environment API — what is covered, how the infrastructure is set up, and how to run the tests.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Test Infrastructure](#test-infrastructure)
   - [Unit Tests](#unit-test-infrastructure)
   - [Integration Tests](#integration-test-infrastructure)
4. [Running Tests](#running-tests)
5. [Coverage](#coverage)

---

## Overview

The test suite is split into two layers:

| Layer | Location | Scope |
|---|---|---|
| **Unit** | `research_environment_api/tests/unit/` | Pure logic, no external dependencies. All GCP clients, databases and Celery workers are mocked. |
| **Integration** | `research_environment_api/tests/integration/` | Full HTTP request/response cycle against a real Flask app, a real Postgres DB (Testcontainers), a fake GCS server and Celery in eager mode. |

---

## Prerequisites

- **Docker** – required for integration tests only (Testcontainers spins up Postgres and a fake GCS server automatically).
- Python dependencies from `requirements.txt` installed in your virtual environment.

---

## Test Infrastructure

### Unit Test Infrastructure

`research_environment_api/tests/unit/conftest.py`

| Fixture | Scope | Description |
|---|---|---|
| `mock_config` | function | Patches `create_config` to return a `MagicMock` with sensible defaults (`project_id`, `organization_id`, etc.). |
| `setup_app_config` | function (autouse) | Injects the mocked config into the global app object so service imports find `app.config`. |
| `app` | function | Creates the Flask app with all DB engines patched out — no real DB connection is made. |
| `client` | function | Flask test client backed by the unit `app`. |
| `mock_db_session` | function | Replaces `core_app.database_session` with a `MagicMock` context manager. |

A session-scoped module-level patch disables `generate_required_maps()` (which calls the GCP Compute Engine API at import time) for the entire unit test session.

---

### Integration Test Infrastructure

`research_environment_api/tests/integration/conftest.py`

#### Containers (session-scoped)

| Fixture | Image | Purpose |
|---|---|---|
| `postgres_container` | `postgres:13-alpine` | Real Postgres DB. Alembic migrations are applied once per session. |
| `gcs_emulator_container` | `fsouza/fake-gcs-server:latest` | Fake GCS server. Bucket CRUD operations go to this emulator instead of Google Cloud. |

#### Database

| Fixture | Scope | Description |
|---|---|---|
| `db_engine` | session | SQLAlchemy engine pointing at the container DB. Runs `alembic upgrade head` once. |
| `db_session` | function | Opens a connection, wraps each test in a transaction, and rolls it back afterwards — full test isolation with zero data bleed between tests. |

#### Application

| Fixture | Scope | Description |
|---|---|---|
| `fake_gcs_client` | session | `google-cloud-storage` client configured to point at the emulator. |
| `mock_gcp_environment` | function | Patches `google.cloud.storage.Client` to always use the emulator client. |
| `app` | function | Flask app with the DB engine and GCS client patched in. Auth (`validate_token`) is bypassed globally so tests don't need real tokens. |
| `client` | function | Flask test client backed by the integration `app`. |

#### Celery

| Fixture | Scope | Description |
|---|---|---|
| `celery_eager` | function | Sets `task_always_eager=True` so Celery tasks run synchronously in-process. Uses an independent DB session for task execution to avoid nested transaction issues. |

---

## Running Tests

All commands use `make`. The Makefile selects the local `venv/python/bin/python` when available, and falls back to the system `python3`.

### All tests

```bash
make test
```

```bash
make test-verbose
```

### Unit tests only

```bash
# All unit tests
make test-unit

# Services sub-suite only
make test-unit-services

# Background sub-suite only
make test-unit-background
```

### Integration tests only

```bash
# All integration tests
make test-integration

# Individual suites
make test-integration-workspace
make test-integration-workbench
make test-integration-sharing
make test-integration-monitoring
make test-integration-workflow
```

---

## Coverage

Coverage is collected over the `research_environment_api` package (excluding `wsgi.py`, `worker.py`, test files, and `__init__.py`).

```bash
# Terminal summary
make coverage

# Full HTML report (opens in browser)
make coverage-html
```

The HTML report is written to `htmlcov/index.html`.

