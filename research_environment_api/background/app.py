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
        "export-active-users-per-dataset-weekly": {
            "task": "research_environment_api.background.tasks.export_active_users_per_dataset",
            "schedule": crontab(hour="0", minute=0, day_of_week=6),
            "args": (),
        },
        "export-datasets-total-usage-time-weekly": {
            "task": "research_environment_api.background.tasks.export_datasets_total_usage_time",
            "schedule": crontab(hour=0, minute=0, day_of_week=6),
            "args": (),
        },
        "mark-stale-workbenches-every-six-hours": {
            "task": "research_environment_api.background.tasks.mark_monitoring_entry_for_stale_workbenches",
            "schedule": crontab(minute=0, hour="*/6"),
            "args": (),
        },
    }
