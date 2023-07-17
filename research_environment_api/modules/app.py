from celery import Celery
from sqlalchemy.engine.base import Engine as DatabaseEngine
from sqlalchemy.orm import Session as DatabaseSession

from research_environment_api.modules.celery import create_celery
from research_environment_api.modules.config import Config, create_config
from research_environment_api.modules.db import (
    create_cloud_sql_engine,
    create_sql_engine,
)


class Application:
    def __init__(self):
        self._config = None
        self._database_engine = None
        self._celery_app = None

    def initialize(self, init_db=True, init_celery=False):
        self._config = create_config()
        if init_db:
            self._database_engine = (
                create_sql_engine(self.config.database_url)
                if self.config.is_development()
                else create_cloud_sql_engine(
                    self.config.service_account_credentials,
                    self.config.cloud_sql_instance_connection_name,
                    self.config.database_user,
                    self.config.database_password,
                    self.config.database_name,
                )
            )

        if init_celery:
            self._celery_app = create_celery(
                self.config.celery_broker_url, self.config.celery_result_backend
            )

    def database_session(self) -> DatabaseSession:
        return DatabaseSession(self.database_engine)

    @property
    def config(self) -> Config:
        if not self._config:
            raise Exception("The config was not initialized for the Application.")

        return self._config

    @property
    def database_engine(self) -> DatabaseEngine:
        if not self._database_engine:
            raise Exception(
                "The database engine was not initialized for the Application."
            )

        return self._database_engine

    @property
    def celery_app(self) -> Celery:
        if not self._celery_app:
            raise Exception(
                "The Celery application was not initialized for the Application."
            )

        return self._celery_app


app = Application()
