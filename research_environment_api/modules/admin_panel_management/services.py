import logging
import secrets

from typing import Dict, List, Optional, Tuple, Any, Iterable

from celery.result import AsyncResult
from sqlalchemy import desc, asc, or_, func

from research_environment_api.background.enums import BuildType, WorkflowStatus
from research_environment_api.modules.admin_panel_management.cache import (
    get_inspector_data,
)
from research_environment_api.modules.admin_panel_management.entities import (
    Task,
    TaskOperationResult,
    WorkerStats,
)
from research_environment_api.modules.monitoring_management.models import WorkbenchActivity
from research_environment_api.modules.workbench_management.services import (
    list_workbenches,
)
from research_environment_api.modules.workspace_management.services import (
    _list_all_active_google_projects,
)
from research_environment_api.modules.workbench_management.entities import (
    Workbench,
    WorkbenchDestroy,
    WorkbenchToggleState,
    WorkbenchType,
)
from research_environment_api.modules.admin_panel_management import utils
from research_environment_api.modules.monitoring_management import monitoring
from research_environment_api.modules.app import app
from research_environment_api.worker import app as celery_app
from research_environment_api.modules.common.error_handlers import safe_google_service_call
from research_environment_api.background import schedulers


def authenticate_admin(username: str, password: str) -> bool:
    return (
        secrets.compare_digest(username, app.config.admin_panel_username)
        and secrets.compare_digest(password, app.config.admin_panel_password)
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


def get_event_workbenches() -> tuple[Iterable, list[dict]]:
    gcp_projects = _list_all_active_google_projects()

    project_ids = {project.project_id for project in gcp_projects}

    workflows_in_progress = monitoring.list_all_active_workflows()

    all_workbenches = []
    all_errors = []

    for gcp_project_id in project_ids:
        workbenches, error = safe_google_service_call(
            func=lambda pid=gcp_project_id: list_workbenches(
                gcp_project_id=pid,
                workflows_in_progress=workflows_in_progress,
            ),
            resource_id=gcp_project_id,
            service_name="Workbench Management",
            operation="list_workbenches",
            default_return=[],
        )

        if error:
            all_errors.append(
                {
                    "project_id": gcp_project_id,
                    "gcp_console_url": f"https://console.cloud.google.com/compute/instances?project={gcp_project_id}",
                }
            )
        else:
            for wb in workbenches:
                if getattr(wb, "associated_event", None):
                    all_workbenches.append((gcp_project_id, wb))

    return all_workbenches, all_errors


def destroy_event_workbenches(
    workbenches_with_events: Iterable[tuple[str, Workbench]], event_slug: str
):
    for gcp_project_id, workbench in workbenches_with_events:
        if workbench.associated_event == event_slug:
            user_email = f"{workbench.workbench_owner_username}@healthdatanexus.ai"
            workbench_destroy_entity = WorkbenchDestroy(
                workbench_type=workbench.type,
                workspace_project_id=gcp_project_id,
                user_email=user_email,
                workbench_resource_id=workbench.id,
            )
            workbench_type = workbench.type
            if workbench_type == WorkbenchType.JUPYTER:
                schedulers.destroy_jupyter_workbench_flow(
                    workbench_destroy_entity, workbench
                )
            elif workbench_type == WorkbenchType.COLLABORATIVE:
                schedulers.destroy_collaborative_workbench_flow(
                    workbench_destroy_entity, workbench
                )
            elif workbench_type == WorkbenchType.RSTUDIO:
                schedulers.destroy_rstudio_workbench_flow(
                    workbench_destroy_entity, workbench
                )


def stop_event_workbenches(workbenches_with_events: Iterable[tuple[str, Workbench]], event_slug: str):
    for gcp_project_id, workbench in workbenches_with_events:
        if workbench.associated_event == event_slug:
            user_email = f"{workbench.workbench_owner_username}@healthdatanexus.ai"
            workbench_stop_entity = WorkbenchToggleState(
                workbench_type=workbench.type,
                workspace_project_id=gcp_project_id,
                user_email=user_email,
                workbench_resource_id=workbench.id,
            )
            workbench_type = workbench.type
            if workbench_type == WorkbenchType.JUPYTER:
                schedulers.stop_jupyter_workbench(
                    workbench_stop_entity
                )
            elif workbench_type == WorkbenchType.COLLABORATIVE:
                schedulers.stop_collaborative_workbench(workbench_stop_entity)
            elif workbench_type == WorkbenchType.RSTUDIO:
                schedulers.stop_compute_engine_workbench(workbench_stop_entity)


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
    sort_direction: str = "desc"
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