from flask import request

from research_environment_api.web.workspace_management import (
    workspace_management_bp,
    schemas,
)
from research_environment_api.modules.workspace_management import services, entities


@workspace_management_bp.post("/create")
def create_workspace():
    body = request.get_json()
    workspace_creation_request = schemas.WorkspaceCreationRequest().load(body)
    workspace_creation_entity = entities.WorkspaceCreation(**workspace_creation_request)

    created_google_workspace = services.create_workspace(workspace_creation_entity)

    return created_google_workspace.text, 201


@workspace_management_bp.get("/list")
def list_active_workspaces():
    body = request.get_json()
    list_active_workspaces_request = schemas.ListActiveWorkspacesRequest().load(body)
    workspace_list_query_entity = entities.WorkspaceListQuery(
        **list_active_workspaces_request
    )

    google_active_workspaces_list = services.list_active_workspaces(
        workspace_list_query_entity
    )

    return google_active_workspaces_list, 200
