from celery import Celery


def create_celery(broker_url: str, result_backend: str) -> Celery:
    celery = Celery(
        broker=broker_url,
        backend=result_backend,
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
