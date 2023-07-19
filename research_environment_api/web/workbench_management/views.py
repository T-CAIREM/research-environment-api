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

    return 200


@workbench_management_bp.post("/stop/jupyter")
def stop_jupyter_workbench():
    body = request.get_json()
    workbench_stop_request = schemas.JupyterWorkbenchStopRequest().load(body)
    jupyter_workbench_stop_entity = entities.JupyterWorkbenchStop(
        **workbench_stop_request
    )
    services.stop_jupyter_workbench(jupyter_workbench_stop_entity)

    return 200
