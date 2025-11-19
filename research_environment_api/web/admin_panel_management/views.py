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
    return render_template("admin_panel/event_workbenches.html")


@admin_panel_management_bp.get("/events/workbenches/data")
@validate_admin_page_auth
@validate_token
def get_workbenches_data():
    workbenches_list, errors = services.get_event_workbenches()

    workbenches_by_event = {}
    for project_id, workbench in workbenches_list:
        event_slug = workbench.associated_event
        if event_slug not in workbenches_by_event:
            workbenches_by_event[event_slug] = []
        workbenches_by_event[event_slug].append((project_id, workbench))

    serializable_workbenches = {}
    for event_slug, event_workbenches in workbenches_by_event.items():
        serializable_workbenches[event_slug] = [
            (project_id, {
                'id': wb.id,
                'type': wb.type,
                'status': wb.status,
                'workbench_owner_username': wb.workbench_owner_username,
                'associated_event': wb.associated_event
            })
            for project_id, wb in event_workbenches
        ]

    return {
        'workbenches': serializable_workbenches,
        'errors': errors
    }, 200


@admin_panel_management_bp.post("/events/workbenches/stop")
@validate_admin_page_auth
@validate_token
def stop_event_workbench():
    data = request.get_json()
    if not data:
        return {"error": "Missing request data"}, 400

    workbenches_data = data.get("workbenches", [])
    event_slug = data.get("event_slug")

    if not workbenches_data or not event_slug:
        return {"error": "Missing required fields"}, 400

    try:
        all_workbenches, _ = services.get_event_workbenches()

        workbenches_to_stop = [
            (pid, wb) for pid, wb in all_workbenches
            if any(
                pid == w.get("project_id") and wb.id == w.get("workbench_id")
                for w in workbenches_data
            )
        ]

        if not workbenches_to_stop:
            return {"error": "Workbench not found"}, 404

        services.stop_event_workbenches(workbenches_to_stop, event_slug)

        count = len(workbenches_to_stop)
        message = f"Stop initiated for {count} workbench(es)" if count > 1 else "Workbench stop initiated"
        return {"success": True, "message": message}, 200
    except Exception as e:
        return {"error": str(e)}, 500


@admin_panel_management_bp.post("/events/workbenches/destroy")
@validate_admin_page_auth
@validate_token
def destroy_event_workbench():
    data = request.get_json()
    if not data:
        return {"error": "Missing request data"}, 400

    workbenches_data = data.get("workbenches", [])
    event_slug = data.get("event_slug")

    if not workbenches_data or not event_slug:
        return {"error": "Missing required fields"}, 400

    try:
        all_workbenches, _ = services.get_event_workbenches()

        workbenches_to_destroy = [
            (pid, wb) for pid, wb in all_workbenches
            if any(
                pid == w.get("project_id") and wb.id == w.get("workbench_id")
                for w in workbenches_data
            )
        ]

        if not workbenches_to_destroy:
            return {"error": "Workbench not found"}, 404

        services.destroy_event_workbenches(workbenches_to_destroy, event_slug)

        count = len(workbenches_to_destroy)
        message = f"Destroy initiated for {count} workbench(es)" if count > 1 else "Workbench destroy initiated"
        return {"success": True, "message": message}, 200
    except Exception as e:
        return {"error": str(e)}, 500


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
