from flask import request

from research_environment_api.modules.workspace_management import entities, services
from research_environment_api.web.cache import cache
from research_environment_api.web.workspace_management import (
    schemas,
    workspace_management_bp,
)


@workspace_management_bp.post("/create")
def create_workspace():
    body = request.get_json()
    workspace_creation_request = schemas.WorkspaceCreationRequest().load(body)
    workspace_creation_entity = entities.WorkspaceCreation(**workspace_creation_request)

    # cache.delete_memoized(list_active_workspaces, workspace_creation_entity.email_id)
    services.create_workspace(workspace_creation_entity)

    return "", 201


@workspace_management_bp.delete("/<email>/<workspace_id>")
def delete_workspace(email: str, workspace_id: str):
    workspace_deletion_request = schemas.WorkspaceDeletionRequest().load(
        {"email": email, "workspace_id": workspace_id}
    )
    workspace_deletion_entity = entities.WorkspaceDeletion(**workspace_deletion_request)

    cache.delete_memoized(list_active_workspaces, email)
    deleted_google_workspace = services.delete_workspace(workspace_deletion_entity)

    return deleted_google_workspace.text, 201


@workspace_management_bp.get("/<email>")
@cache.cached(timeout=3600)
def list_active_workspaces(email: str):
    list_active_workspaces_request = schemas.ListActiveWorkspacesRequest().load(
        {"email": email}
    )
    workspace_list_query_entity = entities.WorkspaceListQuery(
        **list_active_workspaces_request
    )

    workspaces = services.list_active_workspaces(workspace_list_query_entity)
    serialized_workspaces = schemas.Workspace(many=True).dump(workspaces)

    return serialized_workspaces, 200
