from os import environ
from dataclasses import dataclass, field

import google.auth
import google.cloud.compute
import google.cloud.appengine_admin
import google.cloud.resourcemanager
import google.cloud.billing
from google.oauth2 import service_account
from celery import Celery, Task

from research_environment_api.library.google.billing import BillingClient
from research_environment_api.library.google.workspace import WorkspaceClient
from research_environment_api.library.google.cloud_build import CloudBuildClient
from research_environment_api.library.legacy_api.client import (
    WorkspaceControllerApiClient,
)


def celery_init_app() -> Celery:
    celery = Celery(
        broker=environ["BROKER_URL"],
        backend=environ["RESULT_BACKEND"],
        include=["research_environment_api.modules.workbench_management.tasks"],
    )
    celery.set_default()
    celery.conf.accept_content = [
        "application/json",
        "application/x-python-serialize",
        "pickle",
    ]
    celery.conf.task_serializer = "pickle"
    celery.conf.result_serializer = "pickle"
    return celery


@dataclass(kw_only=True)
class Config:
    database_url: str = environ["DATABASE_URL"]
    project_id: str = environ["PROJECT_ID"]
    organization_domain: str = environ["ORGANIZATION_ID"]
    billing_account_creator_group_id: str = environ["BILLING_ACCOUNT_CREATOR_GROUP_ID"]
    legacy_workspace_api_url: str = environ["CLOUD_RESEARCH_ENVIRONMENTS_API_URL"]
    terraform_branch_name = environ["TERRAFORM_BRANCH_NAME"]
    terraform_repo_name = environ["TERRAFORM_REPO_NAME"]
    jupyter_startup_script = environ["JUPYTER_STARTUP_SCRIPT"]

    legacy_workspace_api_credentials: google.auth.jwt.Credentials = field(init=False)
    service_account_credentials: service_account.Credentials = field(init=False)
    # FIXME: Use only one BillingClient and move the custom logic into `billing_management`
    google_billing_client: BillingClient = field(init=False)
    google_cloud_billing_client: google.cloud.billing.CloudBillingClient = field(
        init=False
    )
    google_cloud_build_client: CloudBuildClient = field(init=False)
    google_workspace_client: WorkspaceClient = field(init=False)
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

    def __post_init__(self):
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
        self.google_cloud_build_client = CloudBuildClient(
            credentials=self.service_account_credentials
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


config = Config()


celery_app = celery_init_app()
