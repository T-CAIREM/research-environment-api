from celery import Celery
from celery.schedules import crontab

from research_environment_api.background.tasks import WorkflowTask


def create_celery(broker_url: str, result_backend: str) -> Celery:
    celery = Celery(
        broker=broker_url,
        backend=result_backend,
        include=["research_environment_api.background.tasks"],
    )
    celery.set_default()
    celery.conf.accept_content = [
        "application/json",
        "application/x-python-serialize",
        "pickle",
    ]
    celery.conf.task_serializer = "pickle"
    celery.conf.result_serializer = "pickle"
    celery.task_cls = WorkflowTask

    _setup_periodic_tasks(celery)

    return celery


def _setup_periodic_tasks(celery: Celery) -> None:
    celery.conf.beat_schedule = {
        # Executes every Sunday morning at midnight
        'export-datasets-csv-weekly': {
            'task': 'research_environment_api.background.tasks.export_csv_reports',
            'schedule': 60.0, #crontab(hour=0, minute=0, day_of_week=7),
            'args': (),
        },
    }
