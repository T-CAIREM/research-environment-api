from enum import StrEnum
from os import environ

import google.auth
import google.cloud.billing
import google.cloud.compute
import google.cloud.devtools.cloudbuild
import google.cloud.resourcemanager
import google.cloud.storage
import google.cloud.notebooks_v2
import google.cloud.resourcemanager_v3

from google.oauth2 import service_account

from research_environment_api.library.google.billing import BillingClient
from research_environment_api.library.google.workspace import WorkspaceClient


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Config:
    def __init__(self, app_env: AppEnv):
        self.app_env = app_env

        self._init_business_logic_config()
        self._init_database_config()
        self._init_google_clients()
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
        self.organization_id = environ.get("ORGANIZATION_ID")
        self.customer_id = environ.get("CUSTOMER_ID")
        self.billing_account_creator_group_id = environ[
            "BILLING_ACCOUNT_CREATOR_GROUP_ID"
        ]
        self.vpc_secure_perimeter_name = environ["VPC_SECURE_PERIMETER_NAME"]
        self.terraform_branch_name = environ["TERRAFORM_BRANCH_NAME"]
        self.terraform_repo_name = environ["TERRAFORM_REPO_NAME"]
        self.jupyter_startup_script = environ["JUPYTER_STARTUP_SCRIPT"]
        self.rstudio_startup_script = environ["RSTUDIO_STARTUP_SCRIPT"]
        self.cloud_build_service_account_name = environ[
            "CLOUD_BUILD_SERVICE_ACCOUNT_NAME"
        ]
        self.rstudio_image_url = environ["RSTUDIO_IMAGE_URL"]
        self.data_project_name = environ["DATA_PROJECT_NAME"]
        self.network_name = environ["NETWORK_NAME"]
        self.rstudio_dns_project = environ["RSTUDIO_DNS_PROJECT"]
        self.rstudio_dns_zone = environ["RSTUDIO_DNS_ZONE"]
        self.rstudio_domain_name = environ["RSTUDIO_DOMAIN_NAME"]
        self.rstudio_ssl_private_key = environ["RSTUDIO_SSL_PRIVATE_KEY"]
        self.rstudio_ssl_certificate = environ["RSTUDIO_SSL_CERTIFICATE"]
        self.sharing_folder_id = environ["SHARING_FOLDER_ID"]
        self.workbenches_parent_project_id = environ["WORKBENCHES_PARENT_PROJECT_ID"]
        self.gcp_signed_url_expiration_time = environ["GCP_SIGNED_URL_EXPIRATION_TIME"]
        self.gcp_cors_allowed_origins = environ["GCP_CORS_ALLOWED_ORIGINS"]

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
        self.admin_directory_client = (
            self.google_workspace_client.admin_directory_client
        )
        self.cloud_identity_client = self.google_workspace_client.cloud_identity_client
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
        self.google_zone_operations_client = google.cloud.compute.ZoneOperationsClient(
            credentials=self.service_account_credentials
        )
        self.google_operations_client = (
            self.google_cloud_build_client._transport.operations_client
        )
        self.google_cloud_storage_client = google.cloud.storage.Client(
            credentials=self.service_account_credentials
        )
        self.google_cloud_notebooks_client = (
            google.cloud.notebooks_v2.NotebookServiceClient(
                credentials=self.service_account_credentials
            )
        )
        self.google_cloud_notebooks_operation_client = (
            self.google_cloud_notebooks_client._transport.operations_client
        )

        self.organization_client = google.cloud.resourcemanager_v3.OrganizationsClient(
            credentials=self.service_account_credentials
        )


def create_config() -> Config:
    if environ["APP_ENV"] == "production":
        app_env = AppEnv.PRODUCTION
    else:
        app_env = AppEnv.DEVELOPMENT

    return Config(app_env=app_env)
