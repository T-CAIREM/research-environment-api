"""Integration test environment defaults.

We set env vars explicitly (instead of relying on load_dotenv/.env files) to keep
integration tests deterministic and isolated from developer machines and CI.

Values here are safe placeholders (not secrets).
"""

from __future__ import annotations

from typing import Dict


def integration_env_vars(*, database_url: str) -> Dict[str, str]:
    """Return env vars required to bootstrap the app during integration tests.

    Args:
        database_url: SQLAlchemy database URL for the test Postgres container.

    Notes:
        - The app Config uses many `os.environ["KEY"]` reads (hard required).
        - Credentials are patched in `tests/integration/conftest.py`.
        - Celery vars must exist even when we later override Celery to eager mode.
    """

    return {
        # App + DB
        "APP_ENV": "development",
        "DATABASE_URL": database_url,
        # Core business configuration
        "PROJECT_ID": "test-project-id",
        "ORGANIZATION_ID": "test-org-id",
        "BILLING_ACCOUNT_CREATOR_GROUP_ID": "test-group-id",
        "VPC_SECURE_PERIMETER_NAME": "test-perimeter",
        "TERRAFORM_BRANCH_NAME": "main",
        "TERRAFORM_REPO_NAME": "infra-repo",
        # Workbench startup scripts
        "JUPYTER_STARTUP_SCRIPT": "gs://test/jupyter.sh",
        "RSTUDIO_STARTUP_SCRIPT": "gs://test/rstudio.sh",
        # Cloud Build / images
        "CLOUD_BUILD_SERVICE_ACCOUNT_NAME": "builder@test.com",
        "RSTUDIO_IMAGE_URL": "gcr.io/test/rstudio",
        # Data plane / networking
        "DATA_PROJECT_NAME": "data-proj",
        "NETWORK_NAME": "default",
        # RStudio DNS + certificate settings
        "RSTUDIO_DNS_PROJECT": "dns-proj",
        "RSTUDIO_DNS_ZONE": "dns-zone",
        "RSTUDIO_DOMAIN_NAME": "test.com",
        "RSTUDIO_CERTIFICATE_SECRET_ID": "cert-secret",
        # Sharing / Workbench parent
        "SHARING_FOLDER_ID": "folder-id",
        "WORKBENCHES_PARENT_PROJECT_ID": "parent-proj",
        # Misc
        "GCP_SIGNED_URL_EXPIRATION_TIME": "3600",
        "GCP_CORS_ALLOWED_ORIGINS": "*",
        "GITHUB_SSH_KEY_KSM_ID": "ssh-key-id",
        "MONITORING_CSV_EXPORTS_ROOT_BUCKET": "monitoring-bucket",
        # Admin panel
        "ADMIN_PANEL_USERNAME": "admin",
        "ADMIN_PANEL_PASSWORD": "password",
        "ADMIN_PANEL_CACHE_TTL": "300",
        # Credentials path (actual reading is patched out in integration conftest)
        "SERVICE_ACCOUNT_CREDENTIALS_PATH": "/dev/null",
        # Celery config required by Config initialization
        "CELERY_BROKER_URL": "memory://",
        "CELERY_RESULT_BACKEND": "cache+memory://",
        # Flask Caching
        "CACHE_TYPE": "SimpleCache",
    }
