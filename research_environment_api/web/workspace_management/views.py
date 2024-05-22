from flask import request

from research_environment_api.modules.workspace_management import entities, services
from research_environment_api.web.decorators import validate_token
from research_environment_api.web.workspace_management import (
    schemas,
    workspace_management_bp,
)


@workspace_management_bp.post("/create")
@validate_token
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

    workbench_activity_id = services.create_workspace(workspace_creation_entity)
    workflow_identifier = schemas.WorkspaceWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 201


@workspace_management_bp.delete("/delete")
@validate_token
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

    workbench_activity_id = services.delete_workspace(workspace_deletion_entity)
    workflow_identifier = schemas.WorkspaceWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 201


@workspace_management_bp.get("/<email>")
@validate_token
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
    serialized_workspaces = schemas.EntityScaffoldingWorkspaceSchema(many=True).dump(
        workspaces
    )

    return serialized_workspaces, 200


@workspace_management_bp.post("/shared/create")
@validate_token
def create_shared_workspace():
    """Creates a shared workspace where buckets will reside
    ---
    post:
      tags:
        - sharing_management
      description: Creates a workspace according to the specification.
      requestBody:
        content:
          application/json:
            schema: SharedWorkspaceCreationSchema
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkspaceWorkflowIdentifier
    """
    body = request.get_json()
    shared_workspace_creation_request = schemas.SharedWorkspaceCreationRequest().load(
        body
    )
    shared_workspace_creation_entity = entities.SharedWorkspaceCreation(
        **shared_workspace_creation_request
    )

    workbench_activity_id = services.create_shared_workspace(
        shared_workspace_creation_entity
    )
    workflow_identifier = schemas.WorkspaceWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 200


@workspace_management_bp.delete("/shared/delete")
@validate_token
def delete_shared_workspace():
    """Deletes the specified shared workspace.
    ---
    delete:
      tags:
        - sharing_management
      description: Deletes the specified shared workspace.
      requestBody:
        content:
          application/json:
            schema: SharedWorkspaceDeletionRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkspaceWorkflowIdentifier
    """
    body = request.get_json()
    workspace_deletion_request = schemas.SharedWorkspaceDeletionRequest().load(body)
    workspace_deletion_entity = entities.SharedWorkspaceDeletion(
        **workspace_deletion_request
    )

    workbench_activity_id = services.delete_shared_workspace(workspace_deletion_entity)
    workflow_identifier = schemas.WorkspaceWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 200


@workspace_management_bp.get("/shared/<email>")
@validate_token
def list_active_shared_workspaces(email: str):
    """Lists active shared workspaces for a specified user.
    ---
    get:
      tags:
        - workspace_management
      description: Lists the active shared workspaces for a specified user.
      parameters:
      - in: path
        name: email
        schema:
          type: string
      responses:
        200:
          description: Returns a list of shared workspaces.
          content:
            application/json:
              schema:
                type: array
                items: SharedWorkspace
    """
    list_active_shared_workspaces_request = (
        schemas.ListActiveSharedWorkspacesRequest().load({"email": email})
    )
    shared_workspace_list_query_entity = entities.SharedWorkspaceListQuery(
        **list_active_shared_workspaces_request
    )

    shared_workspaces = services.list_active_shared_workspaces(
        shared_workspace_list_query_entity
    )
    serialized_shared_workspaces = schemas.EntityScaffoldingWorkspaceSchema(
        many=True
    ).dump(shared_workspaces)

    return serialized_shared_workspaces, 200


@workspace_management_bp.get("/quotas/<region>/<workspace_project_id>")
@validate_token
def list_workspace_quotas(region: str, workspace_project_id: str):
    """Lists limits and current usage for entities.QUOTAS_TO_LIST quotas.
    ---
    post:
      tags:
        - workspace_management
      description: Lists limits and current usage for entities.QUOTAS_TO_LIST quotas.
      requestBody:
        content:
          application/json:
            schema: ListWorkspaceQuotasRequest
      responses:
        200:
          description: Returns a list of dicts containing quota name, limit and current usage.
          content:
            application/json:
              schema:
                type: array
                items: dict
    """
    list_workspace_quotas_request = schemas.ListWorkspaceQuotasRequest().load(
        {"workspace_project_id": workspace_project_id, "region": region}
    )
    workspace_list_quotas_query_entity = entities.WorkspaceListQuotasQuery(
        **list_workspace_quotas_request
    )
    quotas_list = services.list_workspace_quotas(workspace_list_quotas_query_entity)

    return quotas_list, 200
