import logging
import secrets
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from celery.result import AsyncResult
from sqlalchemy import desc, asc, or_, func

from research_environment_api.modules.admin_panel_management.cache import get_inspector_data
from research_environment_api.modules.admin_panel_management.entities import (
    Task,
    TaskResult,
    TaskOperationResult,
    WorkerStats,
)
from research_environment_api.modules.admin_panel_management.utils import (
    get_task_state,
    force_task_state,
    sort_tasks_by_date,
)
from research_environment_api.modules.app import app
from research_environment_api.worker import app as celery_app
from research_environment_api.modules.monitoring_management.models import WorkbenchActivity
from research_environment_api.background.enums import BuildType, WorkflowStatus


def authenticate_admin(username: str, password: str) -> bool:
    return (
        secrets.compare_digest(username, app.config.admin_panel_username)
        and secrets.compare_digest(password, app.config.admin_panel_password)
    )


def search_tasks_by_name(name_fragment: str) -> List[Task]:
    active_tasks, reserved_tasks, scheduled_tasks, _, _ = get_inspector_data()

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
    active_tasks, reserved_tasks, scheduled_tasks, _, _ = get_inspector_data()

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
            force_task_state(task_id, "REVOKED")
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
        tasks = sort_tasks_by_date(tasks, reverse=reverse)

    return tasks


def get_workbench_activities(
    page: int = 1,
    per_page: int = 10,
    status: Optional[str] = None,
    build_type: Optional[str] = None,
    workspace_id: Optional[str] = None,
    workbench_id: Optional[str] = None,
    email: Optional[str] = None,
    search_query: Optional[str] = None,
    sort_by: str = "id",
    sort_direction: str = "desc",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetch workbench activities with pagination and filtering options.

    Args:
        page: Page number, starting from 1
        per_page: Number of items per page
        status: Filter by workflow status
        build_type: Filter by build type
        workspace_id: Filter by workspace ID
        workbench_id: Filter by workbench ID
        email: Filter by invoker email
        search_query: Search across multiple fields
        sort_by: Field to sort by (id, workspace_id, etc.)
        sort_direction: Sort direction ('asc' or 'desc')
        start_date: Filter by activities after this date (not used - model has no date field)
        end_date: Filter by activities before this date (not used - model has no date field)

    Returns:
        Tuple of (list of activities as dicts, total count)
    """
    with app.database_session() as session:
        with session.begin():
            query = session.query(WorkbenchActivity)

            # Apply filters if provided
            if status:
                try:
                    workflow_status = WorkflowStatus[status.upper()]
                    query = query.filter(WorkbenchActivity.build_status == workflow_status)
                except (KeyError, ValueError):
                    # Invalid status, ignore the filter
                    pass

            if build_type:
                try:
                    build_type_enum = BuildType[build_type.upper()]
                    query = query.filter(WorkbenchActivity.build_type == build_type_enum)
                except (KeyError, ValueError):
                    # Invalid build type, ignore the filter
                    pass

            if workspace_id:
                query = query.filter(WorkbenchActivity.workspace_id == workspace_id)

            if workbench_id:
                query = query.filter(WorkbenchActivity.workbench_id == workbench_id)

            if email:
                query = query.filter(WorkbenchActivity.invoker_email.ilike(f"%{email}%"))

            # Search across multiple fields if search_query is provided
            if search_query:
                search_pattern = f"%{search_query}%"
                query = query.filter(
                    or_(
                        WorkbenchActivity.invoker_email.ilike(search_pattern),
                        WorkbenchActivity.workbench_id.ilike(search_pattern),
                        WorkbenchActivity.workspace_id.ilike(search_pattern),
                        WorkbenchActivity.build_error_information.ilike(search_pattern)
                    )
                )

            # Note: The model doesn't have created_at or updated_at fields
            # We'll ignore date filters since they don't apply

            # Get total count before pagination
            total_count = query.count()

            # Apply sorting - default to ID if field doesn't exist
            if hasattr(WorkbenchActivity, sort_by):
                sort_attr = getattr(WorkbenchActivity, sort_by)
                if sort_direction.lower() == "desc":
                    query = query.order_by(desc(sort_attr))
                else:
                    query = query.order_by(sort_attr)
            else:
                # Default sort by id
                query = query.order_by(desc(WorkbenchActivity.id) if sort_direction.lower() == "desc" else WorkbenchActivity.id)

            # Apply pagination
            query = query.offset((page - 1) * per_page).limit(per_page)

            # Execute query and convert results to dictionaries
            activities = []
            for activity in query.all():
                activities.append({
                    "id": activity.id,
                    "invoker_email": activity.invoker_email,
                    "workbench_id": activity.workbench_id,
                    "build_type": activity.build_type.name if activity.build_type else None,
                    "build_status": activity.build_status.name if activity.build_status else None,
                    "workspace_id": activity.workspace_id,
                    "build_error_information": activity.build_error_information,
                })

            return activities, total_count


def get_workbench_activity_details(activity_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific workbench activity.

    Args:
        activity_id: ID of the workbench activity

    Returns:
        Activity details as a dictionary or None if not found
    """
    with app.database_session() as session:
        with session.begin():
            activity = session.query(WorkbenchActivity).filter(
                WorkbenchActivity.id == activity_id
            ).first()

            if not activity:
                return None

            return {
                "id": activity.id,
                "invoker_email": activity.invoker_email,
                "workbench_id": activity.workbench_id,
                "build_type": activity.build_type.name if activity.build_type else None,
                "build_status": activity.build_status.name if activity.build_status else None,
                "workspace_id": activity.workspace_id,
                "build_error_information": activity.build_error_information
            }


def get_workbench_activities_summary() -> Dict[str, Any]:
    """
    Get summary statistics about workbench activities.

    Returns:
        Dictionary with summary statistics
    """
    with app.database_session() as session:
        with session.begin():
            # Count by build type
            build_type_counts = {}
            for build_type in BuildType:
                count = session.query(func.count(WorkbenchActivity.id)).filter(
                    WorkbenchActivity.build_type == build_type
                ).scalar()
                build_type_counts[build_type.name] = count

            # Count by status
            status_counts = {}
            for status in WorkflowStatus:
                count = session.query(func.count(WorkbenchActivity.id)).filter(
                    WorkbenchActivity.build_status == status
                ).scalar()
                status_counts[status.name] = count

            # Total count
            total_count = session.query(func.count(WorkbenchActivity.id)).scalar()

            # Note: We can't calculate recent activities as the model has no date fields
            # Setting recent count to 0
            recent_count = 0

            return {
                "total": total_count,
                "recent": recent_count,
                "by_build_type": build_type_counts,
                "by_status": status_counts
            }
