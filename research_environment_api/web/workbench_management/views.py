from flask import request

from research_environment_api.web.workbench_management import (
    workbench_management_bp,
    schemas,
)
from research_environment_api.modules.workbench_management import services, entities


@workbench_management_bp.post("/create/jupyter")
def create_jupyter_workbench():
    body = request.get_json()
    workbench_creation_request = schemas.JupyterWorkbenchCreationRequest().load(body)
    jupyter_workbench_entity = entities.JupyterWorkbench(**workbench_creation_request)
    services.start_jupyter_notebook(jupyter_workbench_entity)

    return 200


@workbench_management_bp.post("/create/rstudio")
def create_jupyter_workbench():
    body = request.get_json()
    workbench_creation_request = schemas.RstudioWorkbenchCreationRequest().load(body)
    # TODO: implement service that is starting rstudio
    return 200
