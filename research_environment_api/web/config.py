class Config:
    """Base config"""

    BROKER_URL = os.environ["BROKER_URL"]
    CELERY_RESULT_BACKEND = os.environ["RESULT_BACKEND"]


class DevelopmentConfig(Config):
    """Development config"""


class ProductionConfig(Config):
    """Production config"""
