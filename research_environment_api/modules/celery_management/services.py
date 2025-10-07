import logging
from typing import List, Dict, Any, Optional, Set, Union

from celery.result import AsyncResult
from research_environment_api.worker import app as celery_app
from research_environment_api.background.constants import REDIS_PATTERNS
from research_environment_api.modules.celery_management.utils import (
    get_task_state,
    get_broker_client,
    get_backend_client,
    handle_redis_key,
    _to_bytes,
    poll_for_task_in_workers,
    force_task_state,
)
from research_environment_api.modules.celery_management.entities import (
    Task, TaskResult, TaskStatus, TaskOperationResult, WorkerStats
)


def search_tasks_by_name(name_fragment: str) -> List[Task]:
    """
    Search for tasks by name/phrase across workers.

    Args:
        name_fragment: Text to search for in task names

    Returns:
        List of matching Task entities
    """
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
                all_tasks.append(Task(
                    id=task["id"],
                    name=task.get("name"),
                    args=task.get("args"),
                    kwargs=task.get("kwargs"),
                    status=state,
                    worker=worker
                ))

    # Reserved tasks
    for worker, tasks in reserved_tasks.items():
        for task in tasks:
            if name_fragment.lower() in task.get("name", "").lower():
                state = get_task_state(task["id"])
                all_tasks.append(Task(
                    id=task["id"],
                    name=task.get("name"),
                    args=task.get("args"),
                    kwargs=task.get("kwargs"),
                    status=state,
                    worker=worker
                ))

    # Scheduled tasks
    for worker, tasks in scheduled_tasks.items():
        for task in tasks:
            if "request" in task and name_fragment.lower() in task["request"].get("name", "").lower():
                task_data = task["request"]
                state = get_task_state(task_data["id"])
                all_tasks.append(Task(
                    id=task_data["id"],
                    name=task_data.get("name"),
                    args=task_data.get("args"),
                    kwargs=task_data.get("kwargs"),
                    status=state,
                    worker=worker,
                    eta=task.get("eta")
                ))

    return all_tasks


def filter_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    worker: Optional[str] = None,
) -> List[Task]:
    """
    Filter tasks by status, type, worker.

    Args:
        status: Filter by task status (PENDING, STARTED, SUCCESS, FAILURE, etc.)
        task_type: Filter by task type or name
        worker: Filter by worker hostname

    Returns:
        List of matching Task entities
    """
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
                all_tasks.append(Task(
                    id=task["id"],
                    name=task.get("name"),
                    args=task.get("args"),
                    kwargs=task.get("kwargs"),
                    status=state,
                    worker=worker_name
                ))

    # Process reserved tasks
    for worker_name, tasks in reserved_tasks.items():
        for task in tasks:
            if worker and worker != worker_name:
                continue
            if task_type and task_type not in task.get("name", ""):
                continue

            state = get_task_state(task["id"])
            if not status or status.upper() == state.upper():
                all_tasks.append(Task(
                    id=task["id"],
                    name=task.get("name"),
                    args=task.get("args"),
                    kwargs=task.get("kwargs"),
                    status=state,
                    worker=worker_name
                ))

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
                all_tasks.append(Task(
                    id=task_req["id"],
                    name=task_req.get("name"),
                    args=task_req.get("args"),
                    kwargs=task_req.get("kwargs"),
                    status=state,
                    worker=worker_name,
                    eta=task.get("eta")
                ))

    return all_tasks


def purge_tasks() -> int:
    """
    Purge all pending tasks from the queue.

    Returns:
        Number of purged tasks
    """
    return celery_app.control.purge()


def get_task_details(task_id: str) -> Task:
    """
    Get detailed information about a task.

    Args:
        task_id: ID of the task to get details for

    Returns:
        Task entity with detailed information
    """
    result = AsyncResult(task_id, app=celery_app)

    task_result = None
    if result.ready():
        try:
            if not result.failed():
                task_result = TaskResult(value=result.get(timeout=1))
            else:
                task_result = TaskResult(error=str(result.result), traceback=result.traceback)
        except Exception as e:
            task_result = TaskResult(error=f"Error retrieving result: {str(e)}")

    return Task(
        id=task_id,
        status=result.state,
        ready=result.ready(),
        successful=result.successful(),
        failed=result.failed(),
        date_done=result.date_done,
        result=task_result
    )


def list_backend_tasks(limit: int = 100, pattern: str = None) -> List[Task]:
    """
    List tasks stored in the result backend (Redis).

    Args:
        limit: Maximum number of tasks to return
        pattern: Optional name pattern to filter tasks

    Returns:
        List of Task entities from the backend
    """
    backend_client = get_backend_client()
    tasks = []
    count = 0
    logger = logging.getLogger(__name__)

    if backend_client and hasattr(backend_client, 'scan_iter'):
        redis_pattern = "celery-task-meta-*"

        for key in backend_client.scan_iter(match=redis_pattern):
            if count >= limit:
                break

            try:
                task_data = backend_client.get(key)
                task_id = key.decode('utf-8').replace('celery-task-meta-', '')

                if task_data:
                    task = get_task_details(task_id)

                    if not pattern or (
                        (task.name and pattern.lower() in task.name.lower()) or
                        pattern.lower() in task_id.lower()
                    ):
                        tasks.append(task)
                        count += 1
            except Exception as e:
                logger.error(f"Error processing task key {key}: {str(e)}")
                # Add a minimal task object with error info
                tasks.append(Task(
                    id=key.decode('utf-8').replace('celery-task-meta-', ''),
                    result=TaskResult(error=f"Error processing task: {str(e)}")
                ))
    else:
        logger.warning("Direct result backend access not supported")

    return tasks


def get_worker_stats() -> List[WorkerStats]:
    """
    Get statistics about Celery workers.

    Returns:
        List of WorkerStats entities
    """
    i = celery_app.control.inspect()
    stats = i.stats() or {}
    active = i.active() or {}
    registered_tasks = i.registered() or {}

    result = []
    for worker, worker_stats in stats.items():
        result.append(WorkerStats(
            name=worker,
            stats=worker_stats,
            active_tasks=len(active.get(worker, [])),
            registered_tasks=registered_tasks.get(worker, [])
        ))

    return result


def delete_tasks_completely(task_ids: list[str]) -> list[TaskOperationResult]:
    """
    Completely and definitively remove multiple Celery tasks from all possible storage locations.

    This function:
    1. Revokes each task (terminate=True, signal=SIGKILL)
    2. Optionally adds to revoked set (for retry prevention)
    3. Polls workers to confirm disappearance (if available)
    4. Calls task.forget() to remove from backend
    5. Forces state to REVOKED

    Args:
        task_ids: A list of Celery task IDs to delete.

    Returns:
        A list of TaskOperationResult objects for each processed task.
    """
    logger = logging.getLogger(__name__)
    results: list[TaskOperationResult] = []

    for task_id in task_ids:
        success = True

        # Step 1: Revoke (hard terminate)
        try:
            celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

            # Optional: Add manually to revoked set
            try:
                backend = celery_app.backend
                if hasattr(backend, "client"):
                    backend.client.sadd("_celery_revoked", task_id)
            except Exception as e:
                logger.warning(f"[{task_id}] Could not add to revoked set: {e}")
                success = False

            # Optional: Poll workers
            try:
                poll_results = poll_for_task_in_workers(task_id)
                if poll_results.get("status") != "gone":
                    success = False
            except Exception as e:
                logger.debug(f"[{task_id}] Polling error: {e}")
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