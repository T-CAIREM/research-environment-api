from flask import request, render_template, jsonify
from datetime import datetime

from research_environment_api.modules.admin_panel_management import services
from research_environment_api.web.decorators import validate_token, validate_admin_page_auth
from research_environment_api.web.admin_panel_management import (
    admin_panel_management_bp,
    schemas,
)


@admin_panel_management_bp.route('/')
@validate_admin_page_auth
@validate_token
def admin_home():
    """Admin panel home page"""
    return render_template('admin_panel/home.html')


@admin_panel_management_bp.route('/celery')
@validate_admin_page_auth
@validate_token
def celery_management():
    """Celery management page - loads skeleton and data is fetched via API"""
    # Pass empty data initially, it will be loaded by JavaScript
    return render_template(
        'admin_panel/celery_management_home.html',
        worker_stats=[],
        task_counts={'active': 0, 'reserved': 0, 'scheduled': 0, 'completed': 0, 'failed': 0},
        tasks=[],
        search_query=request.args.get('q', '')
    )


@admin_panel_management_bp.route('/api/celery-dashboard-data', methods=['GET'])
@validate_admin_page_auth
@validate_token
def get_celery_dashboard_data():
    """API endpoint to get all celery dashboard data for initial load and refresh"""
    # Get task counts
    task_counts = services.get_task_queue_counts()

    # Get worker stats
    worker_stats = services.get_worker_stats()

    # Get tasks (filtered, sorted and paginated)
    search_query = request.args.get('q', '')
    status = request.args.get('status')
    worker = request.args.get('worker')
    task_type = request.args.get('task_type')

    tasks = services.get_paginated_tasks(
        search_query=search_query,
        status=status,
        worker=worker,
        task_type=task_type,
        limit=20
    )

    # Serialize data
    tasks_schema = schemas.TaskSchema(many=True)
    workers_schema = schemas.WorkerStatsSchema(many=True)

    return jsonify({
        'tasks': tasks_schema.dump(tasks),
        'task_counts': task_counts,
        'worker_stats': workers_schema.dump(worker_stats)
    })


@admin_panel_management_bp.route('/tasks', methods=['GET'])
@validate_admin_page_auth
def get_tasks():
    """API endpoint to get tasks list"""
    status = request.args.get('status')
    worker = request.args.get('worker')
    task_type = request.args.get('task_type')
    limit = int(request.args.get('limit', 100))

    tasks = services.get_paginated_tasks(
        status=status,
        worker=worker,
        task_type=task_type,
        limit=limit
    )

    tasks_schema = schemas.TaskSchema(many=True)
    return jsonify(tasks_schema.dump(tasks))


@admin_panel_management_bp.route('/tasks/search', methods=['GET'])
@validate_admin_page_auth
def search_tasks():
    """API endpoint to search tasks by name"""
    name_fragment = request.args.get('q', '')
    limit = int(request.args.get('limit', 100))

    if not name_fragment or len(name_fragment) < 2:
        return jsonify([])

    tasks = services.get_paginated_tasks(
        search_query=name_fragment,
        limit=limit
    )

    tasks_schema = schemas.TaskSchema(many=True)
    return jsonify(tasks_schema.dump(tasks))


@admin_panel_management_bp.route('/tasks/<task_id>', methods=['GET'])
@validate_admin_page_auth
def get_task_details(task_id):
    """API endpoint to get task details"""
    task = services.get_task_details(task_id)
    task_schema = schemas.TaskSchema()
    return jsonify(task_schema.dump(task))


@admin_panel_management_bp.route('/tasks/purge', methods=['POST'])
@validate_admin_page_auth
def purge_tasks():
    """API endpoint to purge tasks"""
    count = services.purge_tasks()
    return jsonify({'success': True, 'purged_count': count})


@admin_panel_management_bp.route('/tasks/delete', methods=['POST'])
@validate_admin_page_auth
def delete_tasks():
    data = request.get_json()
    if not data or 'task_ids' not in data:
        return jsonify({'error': 'Missing task_ids'}), 400

    results = services.delete_tasks(data['task_ids'])
    results_schema = schemas.TaskOperationResultSchema(many=True)
    return jsonify(results_schema.dump(results))


@admin_panel_management_bp.route('/workers', methods=['GET'])
@validate_admin_page_auth
def get_workers():
    workers = services.get_worker_stats()
    workers_schema = schemas.WorkerStatsSchema(many=True)
    return jsonify(workers_schema.dump(workers))


@admin_panel_management_bp.route('/api/celery-tasks', methods=['GET'])
@validate_admin_page_auth
@validate_token
def get_celery_tasks_api():
    """API endpoint to get celery task data for AJAX refresh"""
    # This endpoint is now less critical but can be kept for specific task-only refreshes
    # Or it can be merged with get_celery_dashboard_data
    task_counts = services.get_task_queue_counts()

    search_query = request.args.get('q', '')
    limit = int(request.args.get('limit', 20))
    status = request.args.get('status')
    worker = request.args.get('worker')
    task_type = request.args.get('task_type')

    tasks = services.get_paginated_tasks(
        search_query=search_query,
        status=status,
        task_type=task_type,
        worker=worker,
        limit=limit
    )

    tasks_schema = schemas.TaskSchema(many=True)

    return jsonify({
        'tasks': tasks_schema.dump(tasks),
        'task_counts': task_counts
    })
