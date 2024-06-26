from flask import request

from research_environment_api.web.decorators import validate_token
from research_environment_api.web.user_group_management import (
    schemas,
    user_group_bp,
)
from research_environment_api.modules.user_group_management import services, entities


@user_group_bp.post("/create")
@validate_token
def create_group():
    """Creates a Google group that is used to manage permissions.
    ---
    post:
      tags:
        - user_group_management
      description: Creates a Google user group used to manage user permissions
      requestBody:
        content:
          application/json:
            schema: UserGroupCreationRequest
      responses:
        200:
          description: Return the group entity.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    user_group_creation = schemas.UserGroupCreationRequest().load(body)
    user_group_entity = entities.UserGroupCreation(
        **user_group_creation,
    )
    group = services.create_group(user_group_entity)
    return group, 201


@user_group_bp.delete("/delete")
@validate_token
def delete_group():
    """Deletes a Google group that is used to manage permissions.
    ---
    post:
      tags:
        - user_group_management
      description: Deletes a Google user group used to manage user permissions
      requestBody:
        content:
          application/json:
            schema: UserGroupDeletionRequest
      responses:
        200:
          description: Return the Google specific deletion response.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    user_group_creation = schemas.UserGroupDeletionRequest().load(body)
    user_group_deletion_entity = entities.UserGroupDeletion(
        **user_group_creation,
    )
    group = services.delete_group(user_group_deletion_entity)
    return group, 200
