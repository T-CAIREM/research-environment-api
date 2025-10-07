import time
import logging
from typing import List, Dict, Any, Optional
from celery.result import AsyncResult
from research_environment_api.worker import app as celery_app
from research_environment_api.background.constants import REDIS_PATTERNS


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


def delete_task_completely(task_id: str) -> Dict[str, Any]:
    """
    Completely and definitively remove a task from all possible storage locations.

    This function is designed to be the most thorough way to remove a task:
    1. Revokes task with terminate and signal=SIGKILL
    2. Polls to ensure task is gone from active/reserved queues
    3. Removes task metadata from result backend
    4. Scans Redis keys for any broker entries (queues, unacked, scheduled, retry)
    5. Calls task.forget() to remove any client-side references
    6. Adds task_id to revoked set to prevent future retries

    Args:
        task_id: The ID of the task to delete

    Returns:
        Dict with detailed operation results
    """
    result = {"task_id": task_id, "operations": {}}
    logger = logging.getLogger(__name__)

    # Step 1: Strong revoke with terminate and SIGKILL
    try:
        # Revoke with both terminate and signal SIGKILL for max force
        celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

        # Add to persistent revoked set to block future retries
        try:
            # Store task_id in Redis so it stays permanently revoked
            backend = celery_app.backend
            if hasattr(backend, "client"):
                # Store in Redis revoked set with no expiry
                backend.client.sadd("_celery_revoked", task_id)
        except Exception as e:
            logger.warning(f"Could not add to revoked set: {e}")

        # Poll for task disappearance from worker queues (best effort)
        i = celery_app.control.inspect()
        gone = False
        for _ in range(5):  # Try for a few iterations
            active = i.active() or {}
            reserved = i.reserved() or {}
            # Check if task_id present in any worker
            found = any(
                any(task.get("id") == task_id for task in tasks)
                for tasks in list(active.values()) + list(reserved.values())
            )
            if not found:
                gone = True
                break
            time.sleep(0.5)  # Brief pause between checks

        result["operations"]["revoke"] = "success" if gone else "revoked but may still be in worker memory"
    except Exception as e:
        result["operations"]["revoke"] = f"failed: {str(e)}"

    # Step 2: Remove from result backend
    backend_keys_removed = []
    try:
        backend = celery_app.backend
        if hasattr(backend, "client"):
            try:
                # Primary result metadata
                backend_key = f"celery-task-meta-{task_id}"
                deleted = backend.client.delete(backend_key)
                if deleted:
                    backend_keys_removed.append(backend_key)

                # Child task results (if any)
                child_key = f"celery-task-children-{task_id}"
                deleted = backend.client.delete(child_key)
                if deleted:
                    backend_keys_removed.append(child_key)

                # Group results (if any)
                group_key = f"celery-taskset-meta-{task_id}"
                deleted = backend.client.delete(group_key)
                if deleted:
                    backend_keys_removed.append(group_key)

                result["operations"]["backend_removal"] = {
                    "status": "success",
                    "keys_removed": backend_keys_removed
                }
            except Exception as e:
                result["operations"]["backend_removal"] = f"failed: {str(e)}"
        else:
            result["operations"]["backend_removal"] = "not supported"
    except Exception as e:
        result["operations"]["backend_removal"] = f"failed: {str(e)}"

    # Step 3: Remove from broker (queues, unacked, etc.)
    removed_details = []
    removed_count = 0
    try:
        # Get broker client
        broker_client = None
        try:
            # Primary approach: get broker connection
            broker_client = celery_app.broker_connection().channel().client
        except Exception:
            # Fallback: try to use backend client if it's the same Redis instance
            try:
                broker_client = getattr(backend, "client", None)
            except Exception:
                pass

        if not broker_client:
            result["operations"]["broker_removal"] = "broker client not available"
            return result

        # Helper to normalize string/bytes
        def _to_bytes(v):
            return v if isinstance(v, (bytes, bytearray)) else str(v).encode()

        tid_bytes = _to_bytes(task_id)

        # Scan Redis for all relevant keys
        seen_keys = set()
        for pattern in REDIS_PATTERNS:
            try:
                for raw_key in broker_client.scan_iter(match=pattern):
                    # Normalize key to string
                    key = raw_key.decode() if isinstance(raw_key, (bytes, bytearray)) else raw_key
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    # Get key type and handle accordingly
                    try:
                        key_type = broker_client.type(key)
                        if isinstance(key_type, (bytes, bytearray)):
                            key_type = key_type.decode()
                    except Exception:
                        continue

                    # Handle different Redis types
                    if key_type == "list":
                        # For list type (queues)
                        try:
                            # Get all list items
                            list_items = broker_client.lrange(key, 0, -1)
                            for item in list_items:
                                # Check if task_id is in the serialized message
                                if tid_bytes in item:
                                    # Remove this specific message
                                    removed = broker_client.lrem(key, 0, item)
                                    if removed:
                                        removed_details.append({
                                            "key": key,
                                            "type": "list",
                                            "removed": removed
                                        })
                                        removed_count += removed
                        except Exception as e:
                            logger.debug(f"Error processing list {key}: {e}")

                    elif key_type == "zset":
                        try:
                            zset_items = broker_client.zrange(key, 0, -1)
                            for item in zset_items:
                                if tid_bytes in item:
                                    # Remove matching item
                                    removed = broker_client.zrem(key, item)
                                    if removed:
                                        removed_details.append({
                                            "key": key,
                                            "type": "zset",
                                            "removed": removed
                                        })
                                        removed_count += removed
                        except Exception as e:
                            logger.debug(f"Error processing zset {key}: {e}")

                    elif key_type == "hash":
                        try:
                            hash_keys = broker_client.hkeys(key)
                            for hash_key in hash_keys:
                                if tid_bytes in hash_key or tid_bytes in broker_client.hget(key, hash_key) or '':
                                    removed = broker_client.hdel(key, hash_key)
                                    if removed:
                                        removed_details.append({
                                            "key": key,
                                            "type": "hash",
                                            "field": hash_key,
                                            "removed": removed
                                        })
                                        removed_count += removed
                        except Exception as e:
                            logger.debug(f"Error processing hash {key}: {e}")

                    elif key_type == "set":
                        # For set type
                        try:
                            if broker_client.sismember(key, task_id) or broker_client.sismember(key, tid_bytes):
                                removed = broker_client.srem(key, task_id) + broker_client.srem(key, tid_bytes)
                                if removed:
                                    removed_details.append({
                                        "key": key,
                                        "type": "set",
                                        "removed": removed
                                    })
                                    removed_count += removed

                            # For sets with complex objects, need to check each member
                            set_items = broker_client.smembers(key)
                            for item in set_items:
                                if tid_bytes in item:
                                    removed = broker_client.srem(key, item)
                                    if removed:
                                        removed_details.append({
                                            "key": key,
                                            "type": "set",
                                            "removed": removed
                                        })
                                        removed_count += removed
                        except Exception as e:
                            logger.debug(f"Error processing set {key}: {e}")
            except Exception as e:
                logger.debug(f"Error scanning with pattern {pattern}: {e}")

        # Record broker removal operations
        result["operations"]["broker_removal"] = {
            "status": "success" if removed_count > 0 else "no entries found",
            "total_removed": removed_count,
            "details": removed_details[:10]
        }
    except Exception as e:
        result["operations"]["broker_removal"] = f"failed: {str(e)}"

    try:
        task_result = AsyncResult(task_id, app=celery_app)
        task_result.forget()
        result["operations"]["forget"] = "success"
    except Exception as e:
        result["operations"]["forget"] = f"failed: {str(e)}"

    return result
