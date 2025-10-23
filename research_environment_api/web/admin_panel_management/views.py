from flask import request, render_template

from research_environment_api.modules.admin_panel_management import services
from research_environment_api.web.admin_panel_management import (
    admin_panel_management_bp,
    schemas,
)
from research_environment_api.web.decorators import (
    validate_token,
    validate_admin_page_auth,
)


def _get_dashboard_data():
    search_query = request.args.get("q", "")
    status = request.args.get("status")
    worker = request.args.get("worker")
    task_type = request.args.get("task_type")

    task_counts = services.get_task_queue_counts()
    worker_stats = services.get_worker_stats()

    debounced_search_query = (
        search_query if search_query and len(search_query) >= 3 else None
    )
    tasks = services.get_tasks(
        search_query=debounced_search_query,
        status=status,
        worker=worker,
        task_type=task_type,
    )

    filter_params = {
        "search_query": search_query,
        "status": status,
        "worker": worker,
        "task_type": task_type,
    }

    return task_counts, worker_stats, tasks, filter_params


@admin_panel_management_bp.get("/")
@validate_admin_page_auth
@validate_token
def admin_home():
    return render_template("admin_panel/home.html")


@admin_panel_management_bp.get("/celery")
@validate_admin_page_auth
@validate_token
def celery_management():
    task_counts, worker_stats, tasks, filter_params = _get_dashboard_data()

    return render_template(
        "admin_panel/celery_management_home.html",
        worker_stats=worker_stats,
        task_counts=task_counts,
        tasks=tasks,
        search_query=filter_params["search_query"],
    )


@admin_panel_management_bp.get("/entries-monitoring")
@validate_admin_page_auth
@validate_token
def entries_monitoring():
    # This is a placeholder for the entries monitoring page
    # You can add actual data fetching logic here when needed
    search_query = request.args.get("q", "")
    entry_type = request.args.get("type")
    status = request.args.get("status")

    return render_template(
        "admin_panel/entries_monitoring.html",
        entries=[],
        search_query=search_query,
        entry_type=entry_type,
        status=status
    )


@admin_panel_management_bp.get("/workbench-activities")
@validate_admin_page_auth
@validate_token
def workbench_activities():
    # Get filter parameters
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    search_query = request.args.get("q", "")
    status = request.args.get("status")
    build_type = request.args.get("build_type")
    workspace_id = request.args.get("workspace_id")
    workbench_id = request.args.get("workbench_id")
    email = request.args.get("email")
    sort_by = request.args.get("sort_by", "id")
    sort_direction = request.args.get("sort_direction", "desc")

    # Get activities data
    activities, total_count = services.get_workbench_activities(
        page=page,
        per_page=per_page,
        status=status,
        build_type=build_type,
        workspace_id=workspace_id,
        workbench_id=workbench_id,
        email=email,
        search_query=search_query if search_query else None,
        sort_by=sort_by,
        sort_direction=sort_direction
    )

    # Get summary statistics
    summary = services.get_workbench_activities_summary()

    # Calculate pagination metadata
    total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
    has_next = page < total_pages
    has_prev = page > 1

    # Prepare filter params for template rendering
    filter_params = {
        "search_query": search_query,
        "status": status,
        "build_type": build_type,
        "workspace_id": workspace_id,
        "workbench_id": workbench_id,
        "email": email,
        "sort_by": sort_by,
        "sort_direction": sort_direction
    }

    # Adding the min and max functions to the template context
    return render_template(
        "admin_panel/workbench_activities.html",
        activities=activities,
        summary=summary,
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        filter_params=filter_params,
        min=min,
        max=max
    )


@admin_panel_management_bp.get("/celery-dashboard-data")
@validate_admin_page_auth
@validate_token
def get_celery_dashboard_data():
    task_counts, worker_stats, tasks, _ = _get_dashboard_data()

    return {
        "tasks": schemas.TaskSchema(many=True).dump(tasks),
        "task_counts": task_counts,
        "worker_stats": schemas.WorkerStatsSchema(many=True).dump(worker_stats),
    }, 200


@admin_panel_management_bp.get("/tasks")
@validate_admin_page_auth
def get_tasks():
    name_fragment = request.args.get("q", "")
    status = request.args.get("status")
    worker = request.args.get("worker")
    task_type = request.args.get("task_type")

    search_query = name_fragment if name_fragment and len(name_fragment) >= 2 else None

    tasks = services.get_tasks(
        search_query=search_query,
        status=status,
        worker=worker,
        task_type=task_type,
    )

    return schemas.TaskSchema(many=True).dump(tasks), 200


@admin_panel_management_bp.post("/tasks/purge")
@validate_admin_page_auth
def purge_tasks():
    count = services.purge_tasks()
    return {"success": True, "purged_count": count}, 200


@admin_panel_management_bp.post("/tasks/delete")
@validate_admin_page_auth
def delete_tasks():
    data = request.get_json()
    if not data or "task_ids" not in data:
        return {"error": "Missing task_ids"}, 400

    results = services.delete_tasks(data["task_ids"])
    return schemas.TaskOperationResultSchema(many=True).dump(results), 200


@admin_panel_management_bp.get("/workers")
@validate_admin_page_auth
def get_workers():
    workers = services.get_worker_stats()
    return schemas.WorkerStatsSchema(many=True).dump(workers), 200
