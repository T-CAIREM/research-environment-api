import os
import time
from collections import namedtuple
from enum import Enum as StrEnum
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from testcontainers.core.container import DockerContainer
from testcontainers.postgres import PostgresContainer

from research_environment_api.modules.app import app as core_app
from research_environment_api.tests.integration.helpers.test_env import (
    integration_env_vars,
)
from research_environment_api.web.app import create_app

# Disable Testcontainers Ryuk (reaper) to avoid connection issues in some environments.
os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

# -----------------------------------------------------------------------------
# Module-level env bootstrap
# -----------------------------------------------------------------------------
# session-scoped fixtures (db_engine) and alembic/env.py call app.initialize()
# before any per-test fixture can set env vars via mocker.patch.dict.
# We use setdefault so real values already in the environment are never overwritten.
# DATABASE_URL placeholder is overwritten by db_engine with the real container URL.
_bootstrap_env = integration_env_vars(database_url="postgresql://placeholder/placeholder")
for _k, _v in _bootstrap_env.items():
    os.environ.setdefault(_k, _v)

# -----------------------------------------------------------------------------
# Import-time patching
# -----------------------------------------------------------------------------
# Workbench code builds a machine-type map at import time via `generate_required_maps()`.
# For integration tests we patch it early to keep startup fast + deterministic.

ComputeEngineMachineResources = namedtuple(
    "ComputeEngineMachineResources", ["cpu", "memory"]
)


def mock_generate_required_maps(project_id):
    machine_types_dict = {"N1_STANDARD_1": "n1-standard-1"}
    machine_type_enum = StrEnum("MachineType", machine_types_dict)
    machine_type_to_resource_map = {
        "n1-standard-1": ComputeEngineMachineResources(1, 3.75)
    }
    return machine_type_to_resource_map, machine_type_enum


patcher = patch(
    "research_environment_api.modules.workbench_management.utils.generate_required_maps",
    side_effect=mock_generate_required_maps,
)
patcher.start()

# -----------------------------------------------------------------------------
# Containers / Infra
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgres_container():
    """Postgres container for the whole integration test session."""
    with PostgresContainer("postgres:13-alpine", driver="psycopg2") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def gcs_emulator_container():
    """Fake GCS server container used by google-cloud-storage client."""
    with (
        DockerContainer("fsouza/fake-gcs-server:latest")
        .with_exposed_ports(4443)
        .with_command("-scheme http")
    ) as container:
        # Small wait; fake-gcs-server doesn't provide a health endpoint.
        time.sleep(2)
        yield container


# -----------------------------------------------------------------------------
# Database / Migrations
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine(postgres_container):
    """SQLAlchemy engine pointing to the container DB + migrated to HEAD."""
    database_url = postgres_container.get_connection_url()
    engine = create_engine(database_url, pool_pre_ping=True)

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    alembic_cfg.set_main_option("script_location", "alembic")

    # `alembic/env.py` initializes the app and reads DATABASE_URL.
    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url

    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        pytest.fail(f"Failed to apply Alembic migrations: {str(e)}")
    finally:
        if old_db_url:
            os.environ["DATABASE_URL"] = old_db_url
        else:
            del os.environ["DATABASE_URL"]

    return engine


# -----------------------------------------------------------------------------
# GCS emulator client
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def fake_gcs_client(gcs_emulator_container):
    """google-cloud-storage Client configured to talk to the emulator."""
    host = gcs_emulator_container.get_container_host_ip()
    port = gcs_emulator_container.get_exposed_port(4443)
    endpoint = f"http://{host}:{port}"

    return storage.Client(
        credentials=AnonymousCredentials(),
        project="test-project",
        client_options={"api_endpoint": endpoint},
    )


@pytest.fixture
def mock_gcp_environment(fake_gcs_client, mocker):
    """Patch GCS client creation to use emulator; keep other GCP clients per-test."""
    mocker.patch("google.cloud.storage.Client", return_value=fake_gcs_client)
    return fake_gcs_client


# -----------------------------------------------------------------------------
# App factory / Flask client
# -----------------------------------------------------------------------------


@pytest.fixture
def app(db_engine, mock_gcp_environment, mocker):
    """Flask app configured for integration tests."""

    # Route engine creation to the container DB.
    mocker.patch(
        "research_environment_api.modules.app.create_sql_engine", return_value=db_engine
    )
    mocker.patch("research_environment_api.modules.app.create_cloud_sql_engine")

    mocker.patch.dict(os.environ, integration_env_vars(database_url=str(db_engine.url)))

    # Avoid reading real SA JSON from disk.
    mocker.patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        return_value=MagicMock(),
    )

    core_app.initialize(init_db=True)

    flask_app = create_app()
    flask_app.config.update({"TESTING": True, "DEBUG": True})
    yield flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# -----------------------------------------------------------------------------
# DB session (per-test transaction)
# -----------------------------------------------------------------------------


@pytest.fixture
def db_session(app, db_engine):
    """Transactional session scoped to a single test (rolled back afterwards)."""
    connection = db_engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    old_session = core_app.database_session
    core_app.database_session = session

    yield session

    session.remove()
    transaction.rollback()
    connection.close()

    core_app.database_session = old_session


# -----------------------------------------------------------------------------
# Celery eager mode
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def celery_eager_config():
    """Celery runs synchronously/in-process for integration tests."""
    return {
        "task_always_eager": True,
        "task_eager_propagates": True,
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
    }


@pytest.fixture
def celery_eager(celery_eager_config, mocker, db_engine):
    """Enable Celery eager mode and isolate DB sessions for task execution."""
    from research_environment_api.worker import app as celery_app

    celery_app.conf.update(**celery_eager_config)

    # Tasks can run inside request context; give them an independent session
    # to avoid nested transaction issues with `db_session`.
    def _independent_database_session():
        factory = sessionmaker(bind=db_engine)
        return factory()

    mocker.patch.object(
        core_app, "database_session", side_effect=_independent_database_session
    )

    return celery_app


# -----------------------------------------------------------------------------
# External dependency mocks
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_workspace_services(mocker):
    """Patch workspace-project lookup to avoid external calls."""
    mock_workspace = MagicMock()
    mock_workspace.name = "projects/123456789"
    return mocker.patch(
        "research_environment_api.web.workbench_management.views.workspace_services.get_active_google_project",
        return_value=mock_workspace,
    )
