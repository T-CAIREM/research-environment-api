import os

from google.auth import jwt
from google.oauth2 import service_account


class Config:
    """Base config"""

    PROJECT_ID = os.environ["PROJECT_ID"]
    BILLING_ACCOUNT_CREATOR_GROUP_ID = os.environ["BILLING_ACCOUNT_CREATOR_GROUP_ID"]
    SERVICE_ACCOUNT_CREDENTIALS = service_account.Credentials.from_service_account_file(
        os.environ["SERVICE_ACCOUNT_CREDENTIALS_PATH"]
    )
    ORGANIZATION_DOMAIN = "healthdatanexus.ai"
    ORGANIZATION_ID = "3105849901"

    LEGACY_WORKSPACE_API_URL = os.environ["CLOUD_RESEARCH_ENVIRONMENTS_API_URL"]
    LEGACY_WORKSPACE_API_CREDENTIALS = jwt.Credentials.from_service_account_file(
        os.environ["GATEWAY_SERVICE_ACCOUNT_CREDENTIALS_PATH"],
        audience=os.environ["GATEWAY_AUDIENCE"],
    )


class DevelopmentConfig(Config):
    """Development config"""


class ProductionConfig(Config):
    """Production config"""
