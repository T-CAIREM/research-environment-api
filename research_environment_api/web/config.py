import os


class Config:
    """Base config"""

    # BROKER_URL = os.environ["BROKER_URL"]
    # CELERY_RESULT_BACKEND = os.environ["RESULT_BACKEND"]
    BROKER_URL = "redis://localhost:6379"
    CELERY_RESULT_BACKEND = "redis://localhost:6379"


class DevelopmentConfig(Config):
    """Development config"""


class ProductionConfig(Config):
    """Production config"""
