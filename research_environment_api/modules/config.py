from enum import StrEnum
from os import environ

import google.auth
import google.cloud.appengine_admin
import google.cloud.billing
import google.cloud.compute
import google.cloud.devtools.cloudbuild
import google.cloud.resourcemanager
from google.oauth2 import service_account

from research_environment_api.library.google.billing import BillingClient
from research_environment_api.library.google.workspace import WorkspaceClient
from research_environment_api.library.legacy_api.client import (
    WorkspaceControllerApiClient,
)


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Config:
    def __init__(self, app_env: AppEnv):
        self.app_env = app_env

        self._init_business_logic_config()
        self._init_database_config()
        self._init_google_clients()
        self._init_legacy_workspace_controller_config()
        self._init_celery_config()

    def is_development(self):
        return self.app_env == AppEnv.DEVELOPMENT

    def is_production(self):
        return self.app_env == AppEnv.PRODUCTION

    def _init_business_logic_config(self):
        self.project_id = environ["PROJECT_ID"]
        self.organization_domain = environ.get(
            "ORGANIZATION_DOMAIN", "healthdatanexus.ai"
        )
        self.billing_account_creator_group_id = environ[
            "BILLING_ACCOUNT_CREATOR_GROUP_ID"
        ]
        self.perimeter_name = environ["PERIMETER_NAME"]
        self.terraform_branch_name = environ["TERRAFORM_BRANCH_NAME"]
        self.terraform_repo_name = environ["TERRAFORM_REPO_NAME"]
        self.jupyter_startup_script = environ["JUPYTER_STARTUP_SCRIPT"]

    def _init_database_config(self):
        if self.is_development():
            self.database_url = environ["DATABASE_URL"]
        else:
            self.database_name = environ["DATABASE_NAME"]
            self.cloud_sql_instance_connection_name = environ[
                "CLOUD_SQL_INSTANCE_CONNECTION_NAME"
            ]

    def _init_celery_config(self):
        self.celery_broker_url = environ["CELERY_BROKER_URL"]
        self.celery_result_backend = environ["CELERY_RESULT_BACKEND"]

    def _init_google_clients(self):
        self.service_account_credentials = (
            service_account.Credentials.from_service_account_file(
                environ["SERVICE_ACCOUNT_CREDENTIALS_PATH"]
            )
        )
        self.google_billing_client = BillingClient(
            credentials=self.service_account_credentials,
        )
        self.google_cloud_billing_client = google.cloud.billing.CloudBillingClient(
            credentials=self.service_account_credentials,
        )
        self.google_workspace_client = WorkspaceClient(
            credentials=self.service_account_credentials
        )
        self.google_cloud_resource_client = google.cloud.resourcemanager.ProjectsClient(
            credentials=self.service_account_credentials
        )
        self.google_cloud_build_client = (
            google.cloud.devtools.cloudbuild.CloudBuildClient(
                credentials=self.service_account_credentials
            )
        )
        self.google_compute_engine_instances_client = (
            google.cloud.compute.InstancesClient(
                credentials=self.service_account_credentials
            )
        )
        self.google_app_engine_services_client = (
            google.cloud.appengine_admin.ServicesClient(
                credentials=self.service_account_credentials,
            )
        )
        self.google_app_engine_versions_client = (
            google.cloud.appengine_admin.VersionsClient(
                credentials=self.service_account_credentials,
            )
        )

    def _init_legacy_workspace_controller_config(self):
        credentials = google.auth.jwt.Credentials.from_service_account_file(
            environ["GATEWAY_SERVICE_ACCOUNT_CREDENTIALS_PATH"],
            audience=environ["GATEWAY_AUDIENCE"],
        )
        self.legacy_workspace_controller_client = WorkspaceControllerApiClient(
            credentials=credentials,
            api_url=environ["CLOUD_RESEARCH_ENVIRONMENTS_API_URL"],
        )


def create_config() -> Config:
    if environ["APP_ENV"] == "production":
        app_env = AppEnv.PRODUCTION
    else:
        app_env = AppEnv.DEVELOPMENT

    return Config(app_env=app_env)
