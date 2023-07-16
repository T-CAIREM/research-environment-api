from celery import Celery

from research_environment_api.modules.config import Config


def make_celery(config: Config) -> Celery:
    celery = Celery(
        broker=config.celery_broker_url,
        backend=config.celery_result_backend,
        include=["research_environment_api.modules.celery_management.tasks"],
    )
    celery.set_default()
    celery.conf.accept_content = [
        "application/json",
        "application/x-python-serialize",
        "pickle",
    ]
    celery.conf.task_serializer = "pickle"
    celery.conf.result_serializer = "pickle"

    return celery
