from flask import request

from research_environment_api.modules.workbench_management import entities, services
from research_environment_api.web.workbench_management import (
    schemas,
    workbench_management_bp,
)


@workbench_management_bp.post("/create")
def create_workbench():
    body = request.get_json()
    workbench_creation_request = schemas.WorkbenchCreationRequest().load(body)
    workbench_entity = entities.WorkbenchUpdateCreate(**workbench_creation_request)
    services.schedule_workbench_create(workbench_entity)

    return "", 200


@workbench_management_bp.post("/stop")
def stop_workbench():
    body = request.get_json()
    workbench_stop_request = schemas.WorkbenchStopRequest().load(body)
    workbench_stop_entity = entities.WorkbenchStop(**workbench_stop_request)
    services.schedule_workbench_stop(workbench_stop_entity)

    return "", 200


@workbench_management_bp.post("/update")
def update_workbench():
    body = request.get_json()
    workbench_update_request = schemas.WorkbenchUpdateRequest().load(body)
    workbench_update_entity = entities.WorkbenchUpdateCreate(**workbench_update_request)
    services.schedule_workbench_update(workbench_update_entity)

    return 200
