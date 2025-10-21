from celery.result import AsyncResult
from datetime import datetime
from typing import List

from research_environment_api.modules.admin_panel_management.entities import Task
from research_environment_api.worker import app as celery_app


def get_task_state(task_id: str) -> str:
    """
    Get the real state of a task from the result backend.
    """
    result = AsyncResult(task_id, app=celery_app)
    return result.state


def force_task_state(task_id: str, state: str = "REVOKED"):
    backend = celery_app.backend
    backend.store_result(task_id, None, state)


def sort_tasks_by_date(tasks: List[Task], reverse: bool = True) -> List[Task]:
    def get_sort_key(task):
        if task.date_done is None:
            return datetime.min
        return task.date_done

    tasks.sort(key=get_sort_key, reverse=reverse)
    return tasks
