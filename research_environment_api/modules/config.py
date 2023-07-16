from dataclasses import dataclass, field
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


@dataclass(kw_only=True)
class Config:
    # App Config
    app_env: AppEnv

    # Database Config
    database_url: str = field(init=False)
    database_user: str = field(init=False)
    database_password: str = field(init=False)
    database_name: str = field(init=False)
    cloud_sql_instance_connection_name: str = field(init=False)

    # Google Client Config
    legacy_workspace_api_credentials: google.auth.jwt.Credentials = field(init=False)
    service_account_credentials: service_account.Credentials = field(init=False)
    # FIXME: Use only one BillingClient and move the custom logic into `billing_management`
    google_billing_client: BillingClient = field(init=False)
    google_cloud_billing_client: google.cloud.billing.CloudBillingClient = field(
        init=False
    )
    google_workspace_client: WorkspaceClient = field(init=False)
    google_cloud_build_client: google.cloud.devtools.cloudbuild.CloudBuildClient = (
        field(init=False)
    )
    google_cloud_resource_client: google.cloud.resourcemanager.ProjectsClient = field(
        init=False
    )
    google_compute_engine_instances_client: google.cloud.compute.InstancesClient = (
        field(init=False)
    )
    google_app_engine_services_client: google.cloud.appengine_admin.ServicesClient = (
        field(init=False)
    )
    google_app_engine_versions_client: google.cloud.appengine_admin.VersionsClient = (
        field(init=False)
    )
    legacy_workspace_controller_client: WorkspaceControllerApiClient = field(init=False)

    # Business Logic Config
    project_id: str = field(init=False)
    organization_domain: str = field(init=False)
    billing_account_creator_group_id: str = field(init=False)
    legacy_workspace_api_url: str = field(init=False)
    terraform_branch_name: str = field(init=False)
    terraform_repo_name: str = field(init=False)
    jupyter_startup_script: str = field(init=False)

    # Celery Config
    celery_broker_url: str = field(init=False)
    celery_result_backend: str = field(init=False)

    def __post_init__(self):
        if self.is_development():
            self.database_url = environ["DATABASE_URL"]
        else:
            self.database_user = environ["DATABASE_USER"]
            self.database_password = environ["DATABASE_PASSWORD"]
            self.database_name = environ["DATABASE_NAME"]
            self.cloud_sql_instance_connection_name = environ[
                "CLOUD_SQL_INSTANCE_CONNECTION_NAME"
            ]

        self.project_id = environ["PROJECT_ID"]
        self.organization_domain = environ["ORGANIZATION_ID"]
        self.billing_account_creator_group_id = environ["BILLING_ACCOUNT_CREATOR_GROUP_ID"]
        self.legacy_workspace_api_url = environ["CLOUD_RESEARCH_ENVIRONMENTS_API_URL"]
        self.terraform_branch_name = environ["TERRAFORM_BRANCH_NAME"]
        self.terraform_repo_name = environ["TERRAFORM_REPO_NAME"]
        self.jupyter_startup_script = environ["JUPYTER_STARTUP_SCRIPT"]

        self.legacy_workspace_api_credentials = (
            google.auth.jwt.Credentials.from_service_account_file(
                environ["GATEWAY_SERVICE_ACCOUNT_CREDENTIALS_PATH"],
                audience=environ["GATEWAY_AUDIENCE"],
            )
        )
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
        self.legacy_workspace_controller_client = WorkspaceControllerApiClient(
            credentials=self.legacy_workspace_api_credentials,
            api_url=self.legacy_workspace_api_url,
        )

    def is_development(self):
        return self.app_env == AppEnv.DEVELOPMENT

    def is_production(self):
        return self.app_env == AppEnv.PRODUCTION


def make_config() -> Config:
    if environ["APP_ENV"] == "production":
        app_env = AppEnv.PRODUCTION
    else:
        app_env = AppEnv.DEVELOPMENT

    return Config(app_env=app_env)
