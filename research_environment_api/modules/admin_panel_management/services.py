import logging
from typing import List, Optional

from celery.result import AsyncResult

from research_environment_api.modules.admin_panel_management.cache import (
    get_inspector_data,
)
from research_environment_api.modules.admin_panel_management.entities import (
    Task,
    TaskOperationResult,
    WorkerStats,
)
from research_environment_api.modules.admin_panel_management import utils
from research_environment_api.modules.app import app
from research_environment_api.worker import app as celery_app


def authenticate_admin(username: str, password: str) -> bool:
    return (
        username == app.config.admin_panel_username
        and password == app.config.admin_panel_password
    )


def _process_tasks(
    tasks_by_worker: dict,
    is_scheduled: bool = False,
    name_fragment: Optional[str] = None,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    worker_filter: Optional[str] = None,
) -> List[Task]:
    all_tasks = []
    for worker_name, tasks in tasks_by_worker.items():
        if worker_filter and worker_filter != worker_name:
            continue

        for task_data in tasks:
            task_info = task_data
            eta = None
            if is_scheduled:
                if "request" not in task_data:
                    continue
                task_info = task_data["request"]
                eta = task_data.get("eta")

            task_name = task_info.get("name", "")
            task_id = task_info.get("id")

            if not task_id:
                continue

            if name_fragment and name_fragment.lower() not in task_name.lower():
                continue

            if task_type and task_type not in task_name:
                continue

            state = utils.get_task_state(task_id)
            if status and status.upper() != state.upper():
                continue

            all_tasks.append(
                Task(
                    id=task_id,
                    name=task_name,
                    args=task_info.get("args"),
                    kwargs=task_info.get("kwargs"),
                    status=state,
                    worker=worker_name,
                    eta=eta,
                )
            )
    return all_tasks


def search_tasks_by_name(name_fragment: str) -> List[Task]:
    active_tasks, reserved_tasks, scheduled_tasks, _, _ = get_inspector_data()

    all_tasks = []
    all_tasks.extend(_process_tasks(active_tasks, name_fragment=name_fragment))
    all_tasks.extend(_process_tasks(reserved_tasks, name_fragment=name_fragment))
    all_tasks.extend(
        _process_tasks(scheduled_tasks, is_scheduled=True, name_fragment=name_fragment)
    )

    return all_tasks


def filter_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    worker: Optional[str] = None,
) -> List[Task]:
    active_tasks, reserved_tasks, scheduled_tasks, _, _ = get_inspector_data()

    all_tasks = []
    all_tasks.extend(
        _process_tasks(
            active_tasks,
            status=status,
            task_type=task_type,
            worker_filter=worker,
        )
    )
    all_tasks.extend(
        _process_tasks(
            reserved_tasks,
            status=status,
            task_type=task_type,
            worker_filter=worker,
        )
    )
    all_tasks.extend(
        _process_tasks(
            scheduled_tasks,
            is_scheduled=True,
            status=status,
            task_type=task_type,
            worker_filter=worker,
        )
    )

    return all_tasks


def purge_tasks() -> int:
    return celery_app.control.purge()


def get_worker_stats() -> List[WorkerStats]:
    active_tasks, reserved_tasks, scheduled_tasks, stats, workers = get_inspector_data()

    result = []
    for worker, worker_stats in stats.items():
        result.append(
            WorkerStats(
                name=worker,
                stats=worker_stats,
                active_tasks=len(active_tasks.get(worker, [])),
                registered_tasks=reserved_tasks.get(worker, []),
            )
        )

    return result


def delete_tasks(task_ids: list[str]) -> list[TaskOperationResult]:
    logger = logging.getLogger(__name__)
    results: list[TaskOperationResult] = []

    for task_id in task_ids:
        success = True

        # Step 1: Revoke (hard terminate)
        try:
            celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")
        except Exception as e:
            logger.error(f"[{task_id}] Error while revoking: {e}")
            success = False

        # Step 2: Forget backend result
        try:
            AsyncResult(task_id, app=celery_app).forget()
        except Exception as e:
            logger.warning(f"[{task_id}] Error forgetting task: {e}")
            success = False

        # Step 3: Force REVOKED state
        try:
            utils.force_task_state(task_id, "REVOKED")
        except Exception as e:
            logger.warning(f"[{task_id}] Error forcing task state: {e}")
            success = False

        results.append(TaskOperationResult(task_id=task_id, is_successful=success))

    return results


def get_task_queue_counts():
    active_tasks, reserved_tasks, scheduled_tasks, _, _ = get_inspector_data()

    queue_counts = {
        "active": sum(len(tasks) for tasks in active_tasks.values()),
        "reserved": sum(len(tasks) for tasks in reserved_tasks.values()),
        "scheduled": sum(len(tasks) for tasks in scheduled_tasks.values()),
    }

    tasks = filter_tasks()

    status_counts = {
        "completed": len([t for t in tasks if t.status == "SUCCESS"]),
        "failed": len(
            [t for t in tasks if t.status in ("FAILURE", "REVOKED", "REJECTED")]
        ),
    }

    return {**queue_counts, **status_counts}


def get_tasks(
    search_query: str = None,
    status: str = None,
    task_type: str = None,
    worker: str = None,
    sort_by_date: bool = True,
    reverse: bool = True,
) -> List[Task]:
    if search_query and len(search_query) >= 2:
        tasks = search_tasks_by_name(search_query)
    else:
        tasks = filter_tasks(status=status, worker=worker, task_type=task_type)

    if sort_by_date:
        tasks = utils.sort_tasks_by_date(tasks, reverse=reverse)

    return tasks
