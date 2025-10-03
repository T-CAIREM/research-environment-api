import logging
from typing import List, Dict, Any, Optional
from celery.result import AsyncResult
from research_environment_api.worker import app as celery_app


def get_task_state(task_id: str) -> str:
    """
    Get the real state of a task from the result backend.
    """
    result = AsyncResult(task_id, app=celery_app)
    return result.state


def search_tasks_by_name(name_fragment: str) -> List[Dict[str, Any]]:
    """
    Search for tasks by name/phrase across workers.
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
                task["status"] = get_task_state(task["id"])
                task["worker"] = worker
                all_tasks.append(task)

    # Reserved tasks
    for worker, tasks in reserved_tasks.items():
        for task in tasks:
            if name_fragment.lower() in task.get("name", "").lower():
                task["status"] = get_task_state(task["id"])
                task["worker"] = worker
                all_tasks.append(task)

    # Scheduled tasks
    for worker, tasks in scheduled_tasks.items():
        for task in tasks:
            if "request" in task and name_fragment.lower() in task["request"].get("name", "").lower():
                task_data = task["request"]
                task_data["status"] = get_task_state(task_data["id"])
                task_data["eta"] = task.get("eta")
                task_data["worker"] = worker
                all_tasks.append(task_data)

    return all_tasks


def filter_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    worker: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Filter tasks by status, type, worker.
    """
    i = celery_app.control.inspect()
    active_tasks = i.active() or {}
    reserved_tasks = i.reserved() or {}
    scheduled_tasks = i.scheduled() or {}

    all_tasks = []

    def process_tasks(task_list, worker_name, status_label=None, request_key=False):
        for task in task_list:
            task_id = task["id"] if not request_key else task["request"]["id"]
            task_name = task.get("name") if not request_key else task["request"].get("name")
            if worker and worker != worker_name:
                continue
            if task_type and task_type not in task_name:
                continue

            state = get_task_state(task_id)
            task_data = task if not request_key else task["request"]
            task_data.update(
                {
                    "status": state,
                    "worker": worker_name,
                    "eta": task.get("eta") if request_key else None,
                }
            )

            if not status or status.upper() == state.upper():
                all_tasks.append(task_data)

    for worker_name, tasks in active_tasks.items():
        process_tasks(tasks, worker_name)

    for worker_name, tasks in reserved_tasks.items():
        process_tasks(tasks, worker_name)

    for worker_name, tasks in scheduled_tasks.items():
        process_tasks(tasks, worker_name, request_key=True)

    return all_tasks


def purge_tasks() -> int:
    """
    Purge all pending tasks from the queue.
    """
    return celery_app.control.purge()


def get_task_details(task_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a task.
    """
    result = AsyncResult(task_id, app=celery_app)
    task_info = {
        "task_id": task_id,
        "status": result.state,
        "ready": result.ready(),
        "successful": result.successful(),
        "failed": result.failed(),
        "date_done": result.date_done,
    }

    if result.ready():
        try:
            if not result.failed():
                task_info["result"] = result.get(timeout=1)
            else:
                task_info["error"] = str(result.result)
                task_info["traceback"] = result.traceback
        except Exception as e:
            task_info["error"] = f"Error retrieving result: {str(e)}"

    return task_info


def list_backend_tasks(limit: int = 100, pattern: str = None) -> List[Dict[str, Any]]:
    """
    List tasks stored in the result backend (Redis).

    Args:
        limit: Maximum number of tasks to return
        pattern: Optional name pattern to filter tasks

    Returns:
        List of task information dictionaries
    """
    backend = celery_app.backend
    tasks = []
    count = 0

    if hasattr(backend, 'client') and hasattr(backend.client, 'scan_iter'):
        # For Redis backend
        redis_pattern = "celery-task-meta-*"

        for key in backend.client.scan_iter(match=redis_pattern):
            if count >= limit:
                break

            try:
                task_data = backend.client.get(key)
                task_id = key.decode('utf-8').replace('celery-task-meta-', '')

                if task_data:
                    task_info = {
                        'task_id': task_id,
                        'data': str(task_data)
                    }

                    if not pattern or pattern.lower() in task_info['data'].lower():
                        tasks.append(task_info)
                        count += 1
            except Exception as e:
                logging.error(f"Error processing task key {key}: {str(e)}")
    else:
        logging.warning("Direct result backend access not supported")

    return tasks


def delete_task_by_id(task_id: str) -> Dict[str, Any]:
    """
    Permanently delete a task by ID from both broker (Redis) and backend.

    Args:
        task_id: The ID of the task to delete

    Returns:
        Dict with operation results
    """
    result = {"task_id": task_id, "operations": {}}

    # Step 1: Revoke task
    try:
        celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")
        result["operations"]["revoke"] = "success"
    except Exception as e:
        result["operations"]["revoke"] = f"failed: {str(e)}"

    backend = celery_app.backend
    broker = celery_app.broker_connection().channel().client

    # Step 2: Remove task metadata from result backend
    if hasattr(backend, "client"):
        try:
            backend_key = f"celery-task-meta-{task_id}"
            backend.client.delete(backend_key)
        except Exception as e:
            result["operations"]["backend_removal"] = f"failed: {str(e)}"

    # Step 3: Remove task from broker (pending/retry/scheduled)
    try:
        removed = 0

        default_queue = celery_app.conf.task_default_queue or "celery"
        queue_names = [default_queue]

        if hasattr(celery_app.conf, 'task_routes') and celery_app.conf.task_routes:
            for route in celery_app.conf.task_routes.values():
                if isinstance(route, dict) and 'queue' in route:
                    queue_names.append(route['queue'])

        for queue_name in set(queue_names):
            key_type = broker.type(queue_name).decode('utf-8')
            if key_type == 'list':
                removed += broker.lrem(queue_name, 0, task_id)

        for key in ["unacked", "unacked_index", "scheduled"]:
            if broker.exists(key) and broker.type(key).decode() == "zset":
                for item in broker.zrange(key, 0, -1):
                    if task_id.encode() in item:
                        broker.zrem(key, item)

        result["operations"]["broker_removal"] = "success" if removed else "not found"
    except Exception as e:
        result["operations"]["broker_removal"] = f"failed: {str(e)}"

    result = AsyncResult(task_id, app=celery_app)
    result.forget()

    return True

def delete_task_completely(task_id: str) -> bool:
    """
    Forcefully revoke and completely remove a task from Celery + Redis backend.
    Returns True if removed successfully, False otherwise.
    """
    try:
        # Step 1: Revoke task (terminate if running)
        celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

        # Step 2: Remove from result backend (Redis)
        backend = celery_app.backend
        if hasattr(backend, "client"):
            redis_key = f"celery-task-meta-{task_id}"
            deleted = backend.client.delete(redis_key)
            logging.info(f"Deleted keys for {task_id}: {deleted}")
        else:
            logging.warning("Backend is not Redis-like, can't directly delete keys")

        # Step 3: Forget cached state
        result = AsyncResult(task_id, app=celery_app)
        result.forget()

        return True
    except Exception as e:
        logging.error(f"Failed to completely delete task {task_id}: {e}")
        return False
