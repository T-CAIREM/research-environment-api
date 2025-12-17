import logging
import time
from threading import Lock
from typing import Dict, List, Tuple

from research_environment_api.modules.app import app
from research_environment_api.worker import app as celery_app

_CACHE = {
    "last_refresh": None,
    "active_tasks": {},
    "reserved_tasks": {},
    "scheduled_tasks": {},
    "stats": {},
    "workers": [],
    "refreshing": False,
}
_CACHE_LOCK = Lock()


def _perform_inspect_calls() -> Tuple[Dict, Dict, Dict, Dict, List]:
    logger = logging.getLogger(__name__)
    active = reserved = scheduled = stats = {}
    workers = []
    try:
        i = celery_app.control.inspect(timeout=1)
        active = i.active() or {}
        reserved = i.reserved() or {}
        scheduled = i.scheduled() or {}
        stats = i.stats() or {}
        workers = list(stats.keys())
    except Exception as e:
        logger.warning(f"Could not call Celery inspect(): {e}")
    return active, reserved, scheduled, stats, workers


def _refresh_cache() -> None:
    with _CACHE_LOCK:
        if _CACHE.get("refreshing"):
            return
        _CACHE["refreshing"] = True

    try:
        active, reserved, scheduled, stats, workers = _perform_inspect_calls()
        snapshot_time = time.time()
        with _CACHE_LOCK:
            _CACHE["active_tasks"] = active
            _CACHE["reserved_tasks"] = reserved
            _CACHE["scheduled_tasks"] = scheduled
            _CACHE["stats"] = stats
            _CACHE["workers"] = workers
            _CACHE["last_refresh"] = snapshot_time
    finally:
        with _CACHE_LOCK:
            _CACHE["refreshing"] = False


def get_inspector_data() -> Tuple[Dict, Dict, Dict, Dict, List]:
    ttl = int(app.config.admin_panel_cache_ttl)

    with _CACHE_LOCK:
        last = _CACHE.get("last_refresh")
        should_refresh = ttl <= 0 or last is None or (time.time() - last) > ttl

    if should_refresh:
        try:
            _refresh_cache()
        except Exception as e:
            logging.warning(f"Could not refresh Celery inspect cache: {e}")

    with _CACHE_LOCK:
        return (
            dict(_CACHE["active_tasks"]),
            dict(_CACHE["reserved_tasks"]),
            dict(_CACHE["scheduled_tasks"]),
            dict(_CACHE["stats"]),
            list(_CACHE["workers"]),
        )
