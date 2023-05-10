import os

from google.oauth2 import service_account


class Config:
    """Base config"""

    SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]
    PROJECT_ID = os.environ["PROJECT_ID"]
    BILLING_ACCOUNT_CREATOR_GROUP_ID = os.environ["BILLING_ACCOUNT_CREATOR_GROUP_ID"]
    SERVICE_ACCOUNT_CREDENTIALS = service_account.Credentials.from_service_account_file(
        os.environ["SERVICE_ACCOUNT_CREDENTIALS_PATH"]
    )
    ORGANIZATION_DOMAIN = "healthdatanexus.ai"
    ORGANIZATION_ID = "3105849901"


class DevelopmentConfig(Config):
    """Development config"""


class ProductionConfig(Config):
    """Production config"""
