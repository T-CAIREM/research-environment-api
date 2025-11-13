from flask import request, render_template

from research_environment_api.modules.admin_panel_management import services
from research_environment_api.modules.admin_management import services as admin_services
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
    search_query = request.args.get("q", "")

    return render_template(
        "admin_panel/celery_management_home.html",
        search_query=search_query,
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


@admin_panel_management_bp.get("/events/workbenches")
@validate_admin_page_auth
@validate_token
def event_workbenches():
    workbenches, errors = admin_services.get_event_workbenches()

    return render_template(
        "admin_panel/event_workbenches.html",
        workbenches=workbenches,
        errors=errors
    )


@admin_panel_management_bp.post("/events/workbenches/stop")
@validate_admin_page_auth
@validate_token
def stop_event_workbench():
    data = request.get_json()
    if not data:
        return {"error": "Missing request data"}, 400

    project_id = data.get("project_id")
    workbench_id = data.get("workbench_id")
    event_slug = data.get("event_slug")

    if not all([project_id, workbench_id, event_slug]):
        return {"error": "Missing required fields"}, 400

    try:
        all_workbenches, _ = admin_services.get_event_workbenches()
        workbench_to_stop = [
            (pid, wb) for pid, wb in all_workbenches
            if pid == project_id and wb.id == workbench_id
        ]

        if not workbench_to_stop:
            return {"error": "Workbench not found"}, 404

        admin_services.stop_event_workbenches(workbench_to_stop, event_slug)

        return {"success": True, "message": "Workbench stop initiated"}, 200
    except Exception as e:
        return {"error": str(e)}, 500


@admin_panel_management_bp.post("/events/workbenches/destroy")
@validate_admin_page_auth
@validate_token
def destroy_event_workbench():
    data = request.get_json()
    if not data:
        return {"error": "Missing request data"}, 400

    project_id = data.get("project_id")
    workbench_id = data.get("workbench_id")
    event_slug = data.get("event_slug")

    if not all([project_id, workbench_id, event_slug]):
        return {"error": "Missing required fields"}, 400

    try:
        all_workbenches, _ = admin_services.get_event_workbenches()
        workbench_to_destroy = [
            (pid, wb) for pid, wb in all_workbenches
            if pid == project_id and wb.id == workbench_id
        ]

        if not workbench_to_destroy:
            return {"error": "Workbench not found"}, 404

        admin_services.destroy_event_workbenches(workbench_to_destroy, event_slug)

        return {"success": True, "message": "Workbench destroy initiated"}, 200
    except Exception as e:
        return {"error": str(e)}, 500
