from typing import Optional
from functools import cache
from dataclasses import dataclass, field, fields

from flask import current_app
from google.oauth2 import service_account
import google.auth.jwt as jwt

from research_environment_api.library.google.billing import BillingClient
from research_environment_api.library.google.workspace import WorkspaceClient
from research_environment_api.library.google.cloud_resource import CloudResourceClient
from research_environment_api.library.legacy_api.client import (
    WorkspaceControllerApiClient,
)


@dataclass(kw_only=True)
class Config:
    organization_id: str
    organization_domain: str
    service_account_credentials: Optional[
        service_account.Credentials
    ] = None  # Use Application Default credentials if None
    billing_account_creator_group_id: str
    legacy_workspace_api_url: str
    legacy_workspace_api_credentials: jwt.Credentials

    google_billing_client: BillingClient = field(init=False)
    google_workspace_client: WorkspaceClient = field(init=False)
    google_cloud_resource_client: CloudResourceClient = field(init=False)
    legacy_workspace_controller_client: WorkspaceControllerApiClient = field(init=False)

    def __post_init__(self):
        self.google_billing_client = BillingClient(
            credentials=self.service_account_credentials
        )
        self.google_workspace_client = WorkspaceClient(
            credentials=self.service_account_credentials
        )
        self.google_cloud_resource_client = CloudResourceClient(
            credentials=self.service_account_credentials
        )
        self.legacy_workspace_controller_client = WorkspaceControllerApiClient(
            credentials=self.legacy_workspace_api_credentials,
            api_url=self.legacy_workspace_api_url,
        )

    @classmethod
    def from_flask_config(cls, config):
        config_fields = [field.name for field in fields(cls)]
        lowercase_config = {
            k.lower(): v for k, v in config.items() if k.lower() in config_fields
        }
        return cls(**lowercase_config)


@cache
def app_config():
    """Single dependence between modules and web."""
    return Config.from_flask_config(current_app.config)
