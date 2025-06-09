from flask import request

from research_environment_api.modules.workbench_management import entities, services
from research_environment_api.web.cache import cache
from research_environment_api.web.decorators import validate_token
from research_environment_api.web.workbench_management import (
    schemas,
    workbench_management_bp,
)
from research_environment_api.modules.workspace_management import (
    services as workspace_services,
)


@workbench_management_bp.post("/create")
@validate_token
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

    selected_gpu = workbench_creation_request.get("gpu_accelerator_type")
    if selected_gpu and not services.validate_gpu_accelerator(
        workbench_creation_request["workspace_project_id"],
        selected_gpu,
        workbench_creation_request["workbench_type"],
    ):
        return {
            "error": f"'{selected_gpu}' is not available in GCP. Please try another GPU option."
        }, 500

    # Serves as a form of input validation - is this user the owner of the specified workspace.
    username, domain = workbench_creation_request["user_email"].split("@")
    workspace = workspace_services.get_active_google_project(
        project_id=workbench_creation_request["workspace_project_id"], username=username
    )
    workspace_region = entities.Region(workspace.labels["region"])
    workspace_numeric_id = workspace.name.split("/")[-1]

    workbench_entity = entities.WorkbenchCreate(
        **workbench_creation_request,
        region=workspace_region,
        workspace_numeric_id=workspace_numeric_id,
    )
    workbench_activity_id = services.schedule_workbench_create(workbench_entity)
    workflow_identifier = schemas.WorkbenchWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )

    return workflow_identifier, 200


@workbench_management_bp.put("/stop")
@validate_token
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
@validate_token
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
@validate_token
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
@validate_token
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


@workbench_management_bp.post("/add-collaborator")
@validate_token
def add_collaborator():
    """Adds a collaborator to a workbench.
    ---
    post:
      tags:
        - workbench_management
      description: Adds a collaborator to a workbench by granting roles.
      requestBody:
        content:
          application/json:
            schema: WorkbenchAddCollaboratorRequest
      responses:
        200:
          description: Collaborator added successfully.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    collaborator_data = schemas.WorkbenchCollaboratorRequest().load(body)
    collaborator_entity = entities.WorkbenchCollaborator(**collaborator_data)

    services.add_collaborator_to_workbench(collaborator_entity)
    return {"message": "Collaborator added successfully."}, 200
