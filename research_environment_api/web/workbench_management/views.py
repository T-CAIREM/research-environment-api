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


@workbench_management_bp.post("/collaborators")
@validate_token
def add_collaborators():
    """Adds collaborators to a workbench.
    ---
    post:
      tags:
        - workbench_management
      description: Adds collaborators to a workbench by granting roles.
      requestBody:
        content:
          application/json:
            schema: WorkbenchCollaboratorModificationRequest
      responses:
        200:
          description: Collaborator added successfully.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    collaborator_data = schemas.WorkbenchCollaboratorModificationRequest().load(body)
    collaborator_entity = entities.WorkbenchCollaboratorModification(
        **collaborator_data
    )

    services.add_collaborators_to_workbench(collaborator_entity)
    return {"message": "Collaborators added successfully."}, 200


@workbench_management_bp.delete("/collaborators")
@validate_token
def remove_collaborators():
    """Removes collaborators from a workbench.
    ---
    delete:
      tags:
        - workbench_management
      description: Removes collaborators from a workbench by revoking roles.
      requestBody:
        content:
          application/json:
            schema: WorkbenchCollaboratorModificationRequest
      responses:
        200:
          description: Collaborator removed successfully.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    collaborator_data = schemas.WorkbenchCollaboratorModificationRequest().load(body)
    collaborator_entity = entities.WorkbenchCollaboratorModification(
        **collaborator_data
    )

    services.remove_collaborators_from_workbench(collaborator_entity)
    return {"message": "Collaborators removed successfully."}, 200


@workbench_management_bp.get("/collaborators")
@validate_token
def get_collaborators():
    """Retrieves the list of collaborators for a workbench.
    ---
    get:
      tags:
        - workbench_management
      description: Retrieves the list of collaborators for a workbench.
      parameters:
        - in: query
          name: workbench_id
          schema:
            type: string
      responses:
        200:
          description: Returns the list of collaborators.
          content:
            application/json:
              schema: WorkbenchCollaboratorList
    """
    body = request.get_json()
    get_collaborators_request = schemas.WorkbenchGetCollaboratorsRequest().load(body)
    get_collaborators_entity = entities.WorkbenchGetCollaborators(
        **get_collaborators_request
    )

    collaborators = services.get_workbench_collaborators(get_collaborators_entity)
    serialized_collaborators = schemas.WorkbenchCollaboratorList().dump(collaborators)

    return serialized_collaborators, 200


@workbench_management_bp.get("/notifications")
@validate_token
def get_notifications():
    """Retrieves the list of failed notifications for a workbench.
    ---
    get:
      tags:
        - workbench_management
      description: Retrieves the list of unviewed failed notifications for a workbench.
      requestBody:
        content:
          application/json:
            schema: WorkbenchNotificationRequest
      responses:
        200:
          description: Returns the list of notifications.
          content:
            application/json:
              schema: WorkbenchNotificationList
    """
    body = request.get_json()
    get_notifications_request = schemas.WorkbenchNotificationRequest().load(body)
    get_notifications_entity = entities.WorkbenchGetNotifications(
        **get_notifications_request
    )

    notifications = services.get_workbench_notifications(get_notifications_entity)
    serialized_notifications = schemas.WorkbenchNotificationList().dump(notifications)

    return serialized_notifications, 200


@workbench_management_bp.post("/mark-notification-viewed")
@validate_token
def mark_notification_viewed():
    """Marks a notification as viewed.
    ---
    post:
      tags:
        - workbench_management
      description: Marks a notification as viewed.
      requestBody:
        content:
          application/json:
            schema: NotificationMarkAsViewedRequest
      responses:
        200:
          description: Notification marked as viewed.
    """
    body = request.get_json()
    notification_id = body.get("notification_id")

    result = services.mark_notification_as_viewed(notification_id)

    if result:
        return {"message": "Notification marked as viewed."}, 200
    else:
        return {"error": "Notification not found."}, 404


@workbench_management_bp.delete("/notifications")
@validate_token
def clear_all_notifications():
    """Marks all notifications for a workbench as viewed.
    ---
    delete:
      tags:
        - workbench_management
      description: Marks all unviewed notifications for a workbench as viewed.
      requestBody:
        content:
          application/json:
            schema: WorkbenchNotificationRequest
      responses:
        200:
          description: All notifications marked as viewed.
    """
    body = request.get_json()
    clear_notifications_request = schemas.WorkbenchNotificationRequest().load(body)
    clear_notifications_entity = entities.WorkbenchClearNotifications(
        **clear_notifications_request
    )

    services.clear_all_notifications(clear_notifications_entity)

    return {"message": "All notifications marked as viewed."}, 200


@workbench_management_bp.put("/renew-ssl-certificate")
@validate_token
def renew_rstudio_ssl_certificate():
    """Renews SSL certificate for the Rstudio workbench.
    ---
    put:
      tags:
        - workbench_management
      description: Renews SSL certificate for the Rstudio workbench.
      requestBody:
        content:
          application/json:
            schema: WorkbenchRenewSSLCertificateRequest
      responses:
        200:
          description: Returns the ID of the workflow.
          content:
            application/json:
              schema: WorkbenchWorkflowIdentifier
    """
    body = request.get_json()
    workbench_renewal_request = schemas.WorkbenchRenewSSLCertificateRequest().load(body)
    workbench_renewal_entity = entities.WorkbenchRenewSSLCertificate(**workbench_renewal_request)
    workbench_activity_id = services.schedule_workbench_ssl_certificate_renewal(workbench_renewal_entity)
    workflow_identifier = schemas.WorkbenchWorkflowIdentifier().dump(
        dict(workflow_id=workbench_activity_id)
    )
    return workflow_identifier, 200
