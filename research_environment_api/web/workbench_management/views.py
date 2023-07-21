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
    workbench_entity = entities.WorkbenchCreation(**workbench_creation_request)
    services.create_workbench(workbench_entity)

    return "Workbench creation started", 200


@workbench_management_bp.post("/stop")
def stop_workbench():
    body = request.get_json()
    workbench_stop_request = schemas.WorkbenchStopRequest().load(body)
    workbench_stop_entity = entities.WorkbenchStop(**workbench_stop_request)
    services.stop_workbench(workbench_stop_entity)

    return "Stopping workbench", 200
