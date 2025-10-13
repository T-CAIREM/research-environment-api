import logging
from typing import List, Optional

from celery.result import AsyncResult

from research_environment_api.modules.admin_panel_management.entities import (
    Task,
    TaskResult,
    TaskOperationResult,
    WorkerStats,
)
from research_environment_api.modules.admin_panel_management.utils import (
    get_task_state,
    get_backend_client,
    force_task_state,
)
from research_environment_api.worker import app as celery_app


def search_tasks_by_name(name_fragment: str) -> List[Task]:
    i = celery_app.control.inspect()
    active_tasks = i.active() or {}
    reserved_tasks = i.reserved() or {}
    scheduled_tasks = i.scheduled() or {}

    all_tasks = []

    # Active tasks
    for worker, tasks in active_tasks.items():
        for task in tasks:
            if name_fragment.lower() in task.get("name", "").lower():
                state = get_task_state(task["id"])
                all_tasks.append(
                    Task(
                        id=task["id"],
                        name=task.get("name"),
                        args=task.get("args"),
                        kwargs=task.get("kwargs"),
                        status=state,
                        worker=worker,
                    )
                )

    # Reserved tasks
    for worker, tasks in reserved_tasks.items():
        for task in tasks:
            if name_fragment.lower() in task.get("name", "").lower():
                state = get_task_state(task["id"])
                all_tasks.append(
                    Task(
                        id=task["id"],
                        name=task.get("name"),
                        args=task.get("args"),
                        kwargs=task.get("kwargs"),
                        status=state,
                        worker=worker,
                    )
                )

    # Scheduled tasks
    for worker, tasks in scheduled_tasks.items():
        for task in tasks:
            if (
                "request" in task
                and name_fragment.lower() in task["request"].get("name", "").lower()
            ):
                task_data = task["request"]
                state = get_task_state(task_data["id"])
                all_tasks.append(
                    Task(
                        id=task_data["id"],
                        name=task_data.get("name"),
                        args=task_data.get("args"),
                        kwargs=task_data.get("kwargs"),
                        status=state,
                        worker=worker,
                        eta=task.get("eta"),
                    )
                )

    return all_tasks


def filter_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    worker: Optional[str] = None,
) -> List[Task]:
    i = celery_app.control.inspect()
    active_tasks = i.active() or {}
    reserved_tasks = i.reserved() or {}
    scheduled_tasks = i.scheduled() or {}

    all_tasks = []

    # Process active tasks
    for worker_name, tasks in active_tasks.items():
        for task in tasks:
            if worker and worker != worker_name:
                continue
            if task_type and task_type not in task.get("name", ""):
                continue

            state = get_task_state(task["id"])
            if not status or status.upper() == state.upper():
                all_tasks.append(
                    Task(
                        id=task["id"],
                        name=task.get("name"),
                        args=task.get("args"),
                        kwargs=task.get("kwargs"),
                        status=state,
                        worker=worker_name,
                    )
                )

    # Process reserved tasks
    for worker_name, tasks in reserved_tasks.items():
        for task in tasks:
            if worker and worker != worker_name:
                continue
            if task_type and task_type not in task.get("name", ""):
                continue

            state = get_task_state(task["id"])
            if not status or status.upper() == state.upper():
                all_tasks.append(
                    Task(
                        id=task["id"],
                        name=task.get("name"),
                        args=task.get("args"),
                        kwargs=task.get("kwargs"),
                        status=state,
                        worker=worker_name,
                    )
                )

    # Process scheduled tasks
    for worker_name, tasks in scheduled_tasks.items():
        for task in tasks:
            if "request" not in task:
                continue

            task_req = task["request"]
            if worker and worker != worker_name:
                continue
            if task_type and task_type not in task_req.get("name", ""):
                continue

            state = get_task_state(task_req["id"])
            if not status or status.upper() == state.upper():
                all_tasks.append(
                    Task(
                        id=task_req["id"],
                        name=task_req.get("name"),
                        args=task_req.get("args"),
                        kwargs=task_req.get("kwargs"),
                        status=state,
                        worker=worker_name,
                        eta=task.get("eta"),
                    )
                )

    return all_tasks


def purge_tasks() -> int:
    return celery_app.control.purge()


def get_task_details(task_id: str) -> Task:
    result = AsyncResult(task_id, app=celery_app)

    task_result = None
    if result.ready():
        try:
            if not result.failed():
                task_result = TaskResult(value=result.get(timeout=1))
            else:
                task_result = TaskResult(
                    error=str(result.result), traceback=result.traceback
                )
        except Exception as e:
            task_result = TaskResult(error=f"Error retrieving result: {str(e)}")

    return Task(
        id=task_id,
        status=result.state,
        ready=result.ready(),
        successful=result.successful(),
        failed=result.failed(),
        date_done=result.date_done,
        result=task_result,
    )


def list_backend_tasks(limit: int = 100, pattern: str = None) -> List[Task]:
    backend_client = get_backend_client()
    tasks = []
    count = 0
    logger = logging.getLogger(__name__)

    if backend_client and hasattr(backend_client, "scan_iter"):
        redis_pattern = "celery-task-meta-*"

        for key in backend_client.scan_iter(match=redis_pattern):
            if count >= limit:
                break

            try:
                task_data = backend_client.get(key)
                task_id = key.decode("utf-8").replace("celery-task-meta-", "")

                if task_data:
                    task = get_task_details(task_id)

                    if not pattern or (
                        (task.name and pattern.lower() in task.name.lower())
                        or pattern.lower() in task_id.lower()
                    ):
                        tasks.append(task)
                        count += 1
            except Exception as e:
                logger.error(f"Error processing task key {key}: {str(e)}")
                tasks.append(
                    Task(
                        id=key.decode("utf-8").replace("celery-task-meta-", ""),
                        result=TaskResult(error=f"Error processing task: {str(e)}"),
                    )
                )
    else:
        logger.warning("Direct result backend access not supported")

    return tasks


def get_worker_stats() -> List[WorkerStats]:
    i = celery_app.control.inspect()
    stats = i.stats() or {}
    active = i.active() or {}
    registered_tasks = i.registered() or {}

    result = []
    for worker, worker_stats in stats.items():
        result.append(
            WorkerStats(
                name=worker,
                stats=worker_stats,
                active_tasks=len(active.get(worker, [])),
                registered_tasks=registered_tasks.get(worker, []),
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
            force_task_state(task_id, "REVOKED")
        except Exception as e:
            logger.warning(f"[{task_id}] Error forcing task state: {e}")
            success = False

        results.append(TaskOperationResult(task_id=task_id, is_successful=success))

    return results
