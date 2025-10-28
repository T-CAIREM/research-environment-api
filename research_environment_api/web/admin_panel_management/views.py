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

    tasks = services.get_tasks(
        search_query=search_query,
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
    failed_tasks = any(not result.is_successful for result in results)

    if failed_tasks:
        return {
            "error": "Some tasks could not be deleted.",
        }, 500

    return schemas.TaskOperationResultSchema(many=True).dump(results), 200


@admin_panel_management_bp.get("/workers")
@validate_admin_page_auth
def get_workers():
    workers = services.get_worker_stats()
    return schemas.WorkerStatsSchema(many=True).dump(workers), 200
