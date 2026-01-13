import pytest
from unittest.mock import MagicMock, patch
from enum import Enum
from dotenv import load_dotenv

# 1. Load environment variables from .env file BEFORE importing app modules
load_dotenv()

# Create a mock result for generate_required_maps
# It expects to return: (ResourceMap, MachineTypeEnum)
mock_machine_map = {"n1-standard-1": MagicMock(cpu=1, memory=3.75)}


class MockMachineType(str, Enum):
    N1_STANDARD_1 = "n1-standard-1"


patcher = patch(
    "research_environment_api.modules.workbench_management.utils.generate_required_maps",
    return_value=(mock_machine_map, MockMachineType),
)
patcher.start()

from research_environment_api.web.app import create_app
from research_environment_api.modules.app import app as core_app


@pytest.fixture(scope="session", autouse=True)
def stop_patchers():
    """Cleanup patches at the end of the session."""
    yield
    patcher.stop()


@pytest.fixture
def mock_config(mocker):
    """
    Patches the create_config function to return a MagicMock.
    """
    config_mock = MagicMock()
    config_mock.is_development.return_value = True
    config_mock.project_id = "test-project-id"
    config_mock.organization_id = "test-org-id"
    config_mock.rstudio_image_url = "test-image-url"
    config_mock.organization_domain = "healthdatanexus.ai"

    mocker.patch(
        "research_environment_api.modules.app.create_config", return_value=config_mock
    )

    mocker.patch(
        "research_environment_api.web.app.build_config",
        return_value={"TESTING": True, "SECRET_KEY": "test-key"},
    )
    return config_mock


@pytest.fixture(autouse=True)
def setup_app_config(mock_config):
    """
    Injects the mocked configuration into the global app object.
    Necessary because services.py imports 'app' and uses 'app.config'.
    """
    old_config = getattr(core_app, "_config", None)

    core_app._config = mock_config

    yield

    core_app._config = old_config


@pytest.fixture
def app(mock_config, mocker):
    """
    Initializes the Flask application with mocked dependencies.
    """
    # Prevent SQLAlchemy from trying to connect to a real DB
    mocker.patch("research_environment_api.modules.app.create_sql_engine")
    mocker.patch("research_environment_api.modules.app.create_cloud_sql_engine")

    # Initialize Core App
    core_app.initialize(init_db=True)

    # Create Flask App
    flask_app = create_app()
    flask_app.config.update({"TESTING": True})

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_db_session(mocker):
    """Mocks the database session context manager."""
    mock_session = MagicMock()
    mocker.patch.object(
        core_app,
        "database_session",
        return_value=MagicMock(__enter__=MagicMock(return_value=mock_session)),
    )
    return mock_session
