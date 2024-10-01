from celery import Celery
from celery.schedules import crontab
import logging
import json
from os import environ
from research_environment_api.background.tasks import WorkflowTask
from celery.signals import setup_logging, after_setup_logger


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(log_record)


@setup_logging.connect
def setup_logging(loglevel, **kwargs):
    logger = logging.getLogger()
    logger.propagate = False
    logger.setLevel(loglevel)
    handler = logging.StreamHandler()
    if environ["APP_ENV"] == "production":
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)


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
    celery.conf.worker_hijack_root_logger = False
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
