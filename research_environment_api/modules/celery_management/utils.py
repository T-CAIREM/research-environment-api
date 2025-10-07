import logging
from typing import Dict, Any, Optional
import time

from research_environment_api.worker import app as celery_app
from research_environment_api.background.constants import REDIS_PATTERNS
from celery.result import AsyncResult


def get_task_state(task_id: str) -> str:
    """
    Get the real state of a task from the result backend.
    """
    result = AsyncResult(task_id, app=celery_app)
    return result.state


def get_backend_client():
    """Get a Redis client connected to the result backend"""
    backend = celery_app.backend
    if hasattr(backend, "client"):
        return backend.client
    return None


def force_task_state(task_id: str, state: str = "REVOKED"):
    backend = celery_app.backend
    backend.store_result(task_id, None, state)