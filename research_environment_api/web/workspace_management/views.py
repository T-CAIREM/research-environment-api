from flask import request

from research_environment_api.modules.workbench_management import entities, services
from research_environment_api.web.cache import cache
from research_environment_api.web.workspace_management import (
    schemas,
    workspace_management_bp,
)


@workspace_management_bp.post("/create")
def create_workspace():
    """Creates the specified workspace.
    ---
    post:
      tags:
        - workspace_management
      description: Creates the specified workspace.
      requestBody:
        content:
          application/json:
            schema: WorkspaceCreationRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkspaceWorkflowIdentifier
    """
    body = request.get_json()
    workspace_creation_request = schemas.WorkspaceCreationRequest().load(body)
    workspace_creation_entity = entities.WorkspaceCreation(**workspace_creation_request)

    cache.delete_memoized(list_active_workspaces, workspace_creation_entity.user_email)
    workbench_activity_id = services.create_workspace(workspace_creation_entity)
    workflow_identifier = schemas.WorkspaceWorkflowIdentifier(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 201


@workspace_management_bp.delete("/delete")
def delete_workspace():
    """Deletes the specified workspace.
    ---
    post:
      tags:
        - workspace_management
      description: Deletes the specified workspace.
      requestBody:
        content:
          application/json:
            schema: WorkspaceDeletionRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkspaceWorkflowIdentifier
    """
    body = request.get_json()
    workspace_deletion_request = schemas.WorkspaceDeletionRequest().load(body)
    workspace_deletion_entity = entities.WorkspaceDeletion(**workspace_deletion_request)

    cache.delete_memoized(list_active_workspaces, workspace_deletion_entity.user_email)
    workbench_activity_id = services.delete_workspace(workspace_deletion_entity)
    workflow_identifier = schemas.WorkspaceWorkflowIdentifier.dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 201


@workspace_management_bp.get("/<email>")
def list_active_workspaces(email: str):
    """Lists active workspaces for a specified user.
    ---
    get:
      tags:
        - workspace_management
      description: Lists the active workspaces for a specified user.
      parameters:
      - in: path
        name: email
        schema:
          type: string
      responses:
        200:
          description: Returns a list of workspaces.
          content:
            application/json:
              schema:
                type: array
                items: Workspace
    """
    list_active_workspaces_request = schemas.ListActiveWorkspacesRequest().load(
        {"email": email}
    )
    workspace_list_query_entity = entities.WorkspaceListQuery(
        **list_active_workspaces_request
    )

    workspaces = services.list_active_workspaces(workspace_list_query_entity)
    serialized_workspaces = schemas.Workspace(many=True).dump(workspaces)

    return serialized_workspaces, 200
