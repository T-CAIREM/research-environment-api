from flask import request

from research_environment_api.web.workbench_management import (
    workbench_management_bp,
    schemas,
)
from research_environment_api.modules.workbench_management import services, entities


@workbench_management_bp.post("/create/<instance_type>")
def create_workbench(instance_type: str):
    body = request.get_json()

    if instance_type == "jupyter":
        workbench_creation_request = schemas.JupyterWorkbenchCreationRequest().load(
            body
        )
        jupyter_workbench_entity = entities.JupyterWorkbench(
            **workbench_creation_request
        )
        services.start_jupyter_notebook(jupyter_workbench_entity)
    return 200
