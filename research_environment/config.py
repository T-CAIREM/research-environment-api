import os


class Config(object):
    """Base config"""

    ORGANIZATION_DOMAIN = "healthdatanexus.ai"


class DevelopmentConfig(Config):
    """Development config"""

    PROJECT_ID = os.environ["PROJECT_ID"]
    BILLING_ACCOUNT_CREATOR_GROUP_ID = os.environ["BILLING_ACCOUNT_CREATOR_GROUP_ID"]
