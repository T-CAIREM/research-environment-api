import logging
from typing import Dict, Any, Optional
import time

from research_environment_api.worker import app as celery_app
from research_environment_api.background.constants import REDIS_PATTERNS
from celery.result import AsyncResult


def _to_bytes(v):
    return v if isinstance(v, (bytes, bytearray)) else str(v).encode()


def get_task_state(task_id: str) -> str:
    """
    Get the real state of a task from the result backend.
    """
    result = AsyncResult(task_id, app=celery_app)
    return result.state


def get_broker_client():
    """Get a Redis client connected to the broker"""
    broker_client = celery_app.broker_connection().channel().client
    return broker_client


def get_backend_client():
    """Get a Redis client connected to the result backend"""
    backend = celery_app.backend
    if hasattr(backend, "client"):
        return backend.client
    return None


def handle_redis_key(broker_client, key: str, tid_bytes: bytes, logger: logging.Logger) -> Dict[str, Any]:
    """
    Handle different Redis key types when searching for a task ID

    Args:
        broker_client: Redis client
        key: Redis key name
        tid_bytes: Task ID in bytes
        logger: Logger instance

    Returns:
        Dict with removal information
    """
    removed_details = []
    removed_count = 0

    try:
        key_type = broker_client.type(key)
        if isinstance(key_type, (bytes, bytearray)):
            key_type = key_type.decode()
    except Exception:
        return {"removed": 0, "details": []}

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
        # For sorted sets (scheduled, retry, unacked)
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
        # For hash type (some task metadata)
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
            # Check if task_id is in the set directly
            if broker_client.sismember(key, tid_bytes):
                removed = broker_client.srem(key, tid_bytes)
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

    return {
        "removed": removed_count,
        "details": removed_details
    }


def poll_for_task_in_workers(task_id: str, max_attempts: int = 5, delay: float = 0.5) -> Dict[str, Any]:
    try:
        i = celery_app.control.inspect()
        for attempt in range(max_attempts):
            active = i.active() or {}
            reserved = i.reserved() or {}
            scheduled = i.scheduled() or {}

            found = any(
                any((t.get("id") == task_id) or (t.get("request", {}).get("id") == task_id) for t in tasks)
                for tasks in list(active.values()) + list(reserved.values()) + list(scheduled.values())
            )

            if not found:
                return {"status": "gone", "attempts": attempt + 1}

            time.sleep(delay)

        return {"status": "still_present", "attempts": max_attempts}
    except Exception as e:
        return {"status": "inspect_failed", "error": str(e)}


def force_task_state(task_id: str, state: str = "REVOKED") -> Dict[str, Any]:
    """
    Force a task state in the backend

    Args:
        task_id: The ID of the task
        state: The state to set (default: REVOKED)

    Returns:
        Dict with operation result
    """
    try:
        backend = celery_app.backend
        if hasattr(backend, "store_result"):
            # store_result(task_id, result, status)
            backend.store_result(task_id, None, state)
            return {"status": "success", "state": state}
        else:
            return {"status": "not_supported"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
