from flask import request

from research_environment_api.modules.workbench_management import entities, services
from research_environment_api.web.workbench_management import (
    schemas,
    workbench_management_bp,
)


@workbench_management_bp.post("/create")
def create_workbench():
    body = request.get_json()
    workbench_creation_request = schemas.WorkbenchCreateRequest().load(body)
    workbench_entity = entities.WorkbenchCreate(**workbench_creation_request)
    workflow_id = services.schedule_workbench_create(workbench_entity)

    return workflow_id, 200


@workbench_management_bp.put("/stop")
def stop_workbench():
    body = request.get_json()
    workbench_stop_request = schemas.WorkbenchToggleStateRequest().load(body)
    workbench_stop_entity = entities.WorkbenchToggleState(**workbench_stop_request)
    workflow_id = services.schedule_workbench_stop(workbench_stop_entity)

    return workflow_id, 200


@workbench_management_bp.put("/start")
def start_workbench():
    body = request.get_json()
    workbench_stop_request = schemas.WorkbenchToggleStateRequest().load(body)
    jupyter_workbench_stop_entity = entities.WorkbenchToggleState(
        **workbench_stop_request
    )
    workflow_id = services.schedule_workbench_start(jupyter_workbench_stop_entity)

    return workflow_id, 200


@workbench_management_bp.put("/update")
def update_workbench():
    body = request.get_json()
    workbench_update_request = schemas.WorkbenchUpdateRequest().load(body)
    workbench_update_entity = entities.WorkbenchUpdateDestroy(
        **workbench_update_request
    )
    workflow_id = services.schedule_workbench_update(workbench_update_entity)

    return workflow_id, 200


@workbench_management_bp.delete("/destroy")
def destroy_workbench():
    body = request.get_json()
    workbench_destroy_request = schemas.WorkbenchDestroyRequest().load(body)
    workbench_destroy_entity = entities.WorkbenchUpdateDestroy(
        **workbench_destroy_request
    )
    workflow_id = services.schedule_workbench_destroy(workbench_destroy_entity)

    return workflow_id, 200
