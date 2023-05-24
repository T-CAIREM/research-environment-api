from functools import cache
from dataclasses import dataclass, field, fields

from flask import current_app
from google.oauth2 import service_account

from research_environment_api.library.google.billing import BillingClient


@dataclass(kw_only=True)
class Config:
    organization_id: str
    organization_domain: str
    service_account_credentials: service_account.Credentials
    billing_account_creator_group_id: str
    google_billing_client: BillingClient = field(init=False)

    def __post_init__(self):
        self.google_billing_client = BillingClient(
            credentials=self.service_account_credentials
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
