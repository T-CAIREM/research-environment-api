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
    delete:
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


@user_group_bp.get("/roles")
@validate_token
def list_roles():
    """Lists all predetermined and organization based roles provided by Google.
    ---
    get:
      tags:
        - user_group_management
      description: Lists all predetermined and organization based roles provided by Google
      requestBody:
        content:
          application/json:
            schema: UserGroupRoleListingRequest
      responses:
        200:
          description: Returns a list of Google roles.
          content:
            application/json:
              schema:
    """
    user_group_roles_listing_entity = entities.UserGroupRoleListing()
    role_entity_list = services.get_google_roles_list(user_group_roles_listing_entity)
    roles_list = schemas.GoogleRole(many=True).dump(role_entity_list)
    return roles_list, 200


@user_group_bp.post("/roles/add")
@validate_token
def add_roles():
    """Adds roles to a specific Google Group.
    ---
    post:
      tags:
        - user_group_management
      description: Adds roles to a specific Google Group
      requestBody:
        content:
          application/json:
            schema: GroupRoleListChangeRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    group_role_addition = schemas.GroupRoleListChangeRequest().load(body)
    add_role_to_group_entity = entities.ChangeGroupRoles(**group_role_addition)
    services.add_role_to_group(add_role_to_group_entity)
    return {}, 200


@user_group_bp.post("/roles/remove")
@validate_token
def remove_roles():
    """Removes roles from a specific Google Group.
    ---
    post:
      tags:
        - user_group_management
      description: Removes roles from a specific Google Group
      requestBody:
        content:
          application/json:
            schema: GroupRoleListChangeRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    group_role_addition = schemas.GroupRoleListChangeRequest().load(body)
    remove_role_from_group_entity = entities.ChangeGroupRoles(**group_role_addition)
    services.remove_roles_from_group(remove_role_from_group_entity)
    return {}, 200
