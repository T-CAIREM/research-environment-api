import os

import google.oauth2.service_account


class Config(object):
    """Base config"""

    PROJECT_ID = os.environ["PROJECT_ID"]
    BILLING_ACCOUNT_CREATOR_GROUP_ID = os.environ["BILLING_ACCOUNT_CREATOR_GROUP_ID"]
    SERVICE_ACCOUNT_CREDENTIALS = (
        google.oauth2.service_account.Credentials.from_service_account_file(
            os.environ["SERVICE_ACCOUNT_CREDENTIALS_PATH"]
        )
    )
    ORGANIZATION_DOMAIN = "healthdatanexus.ai"


class DevelopmentConfig(Config):
    """Development config"""

    SQLALCHEMY_DATABASE_URI = "postgresql://localhost:5432/research_environment_api_dev"
