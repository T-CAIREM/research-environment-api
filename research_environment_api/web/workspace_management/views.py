from flask import request

from research_environment_api.web.workspace_management import (
    workspace_management_bp,
    schemas,
)


@workspace_management_bp.post("/create")
def create_workspace():
    body = request.get_json()
    workspace_creation_request = schemas.WorkspaceCreationRequest().load(body)

    return "", 201
