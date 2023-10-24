from flask import request

from research_environment_api.modules.workbench_management import entities, services
from research_environment_api.web.workbench_management import (
    schemas,
    workbench_management_bp,
)


@workbench_management_bp.post("/create")
def create_workbench():
    """Creates a workbench according to the specification.
    ---
    post:
      tags:
        - workbench_management
      description: Creates a workbench according to the specification.
      requestBody:
        content:
          application/json:
            schema: WorkbenchCreateRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkbenchWorkflowIdentifier
    """
    body = request.get_json()
    workbench_creation_request = schemas.WorkbenchCreateRequest().load(body)

    # Serves as a form of input validation - is this user the owner of the specified workspace.
    username, domain = workbench_creation_request["user_email"].split("@")
    workspace = services.get_active_google_project(
        project_id=workbench_creation_request["workspace_project_id"], username=username
    )
    workspace_region = entities.Region(workspace.labels["region"])
    workspace_numeric_id = workspace.name.split("/")[-1]

    workbench_entity = entities.WorkbenchCreate(
        **workbench_creation_request,
        region=workspace_region,
        workspace_numeric_id=workspace_numeric_id
    )
    workbench_activity_id = services.schedule_workbench_create(workbench_entity)
    workflow_identifier = schemas.WorkbenchWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 200


@workbench_management_bp.put("/stop")
def stop_workbench():
    """Stops the specified workbench.
    ---
    put:
      tags:
        - workbench_management
      description: Stops the specified workbench.
      requestBody:
        content:
          application/json:
            schema: WorkbenchToggleStateRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkbenchWorkflowIdentifier
    """
    body = request.get_json()
    workbench_stop_request = schemas.WorkbenchToggleStateRequest().load(body)
    workbench_stop_entity = entities.WorkbenchToggleState(**workbench_stop_request)
    workbench_activity_id = services.schedule_workbench_stop(workbench_stop_entity)
    workflow_identifier = schemas.WorkbenchWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 200


@workbench_management_bp.put("/start")
def start_workbench():
    """Starts the specified workbench.
    ---
    put:
      tags:
        - workbench_management
      description: Starts the specified workbench.
      requestBody:
        content:
          application/json:
            schema: WorkbenchToggleStateRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkbenchWorkflowIdentifier
    """
    body = request.get_json()
    workbench_stop_request = schemas.WorkbenchToggleStateRequest().load(body)
    workbench_stop_entity = entities.WorkbenchToggleState(**workbench_stop_request)
    workbench_activity_id = services.schedule_workbench_start(workbench_stop_entity)
    workflow_identifier = schemas.WorkbenchWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 200


@workbench_management_bp.put("/update")
def update_workbench():
    """Updates the specified workbench.
    ---
    put:
      tags:
        - workbench_management
      description: Updates the specified workbench.
      requestBody:
        content:
          application/json:
            schema: WorkbenchUpdateRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkbenchWorkflowIdentifier
    """
    body = request.get_json()
    workbench_update_request = schemas.WorkbenchUpdateRequest().load(body)
    workbench_update_entity = entities.WorkbenchUpdate(**workbench_update_request)
    workbench_activity_id = services.schedule_workbench_update(workbench_update_entity)
    workflow_identifier = schemas.WorkbenchWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 200


@workbench_management_bp.delete("/destroy")
def destroy_workbench():
    """Destroys the specified workbench.
    ---
    delete:
      tags:
        - workbench_management
      description: Destroys the specified workbench.
      requestBody:
        content:
          application/json:
            schema: WorkbenchDestroyRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkbenchWorkflowIdentifier
    """
    body = request.get_json()
    workbench_destroy_request = schemas.WorkbenchDestroyRequest().load(body)
    workbench_destroy_entity = entities.WorkbenchDestroy(**workbench_destroy_request)
    workbench_activity_id = services.schedule_workbench_destroy(
        workbench_destroy_entity
    )
    workflow_identifier = schemas.WorkbenchWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 200
