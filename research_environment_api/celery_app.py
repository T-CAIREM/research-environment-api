from celery import Celery

from research_environment_api.modules.celery import create_celery
from research_environment_api.modules.config import create_config
from research_environment_api.modules.app import app


class CeleryApplication:
    def __init__(self):
        self._config = create_config()
        self._celery_app = create_celery(
            self._config.celery_broker_url, self._config.celery_result_backend
        )

    def celery_app(self) -> Celery:
        if not self._celery_app:
            raise Exception(
                "The Celery application was not initialized for the Application."
            )

        return self._celery_app


app.initialize()
celery_app = CeleryApplication().celery_app()
