from flask import request

from research_environment_api.modules.sharing_management import entities, services
from research_environment_api.web.sharing_management import (
    sharing_management_bp,
    schemas,
)


@sharing_management_bp.post("/bucket/create")
def create_shared_bucket():
    """Creates shared bucket.
    ---
    post:
      tags:
        - sharing_management
      description: Creates the specified shared workspace.
      requestBody:
        content:
          application/json:
            schema: SharedBucketCreationRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    shared_bucket_creation_request = schemas.SharedBucketCreationRequest().load(body)
    shared_bucket_creation_entity = entities.SharedBucketCreation(
        **shared_bucket_creation_request
    )

    services.create_shared_bucket(shared_bucket_creation_entity)

    return {}, 201


@sharing_management_bp.delete("/bucket/delete")
def delete_shared_bucket():
    """Deletes shared bucket.
    ---
    delete:
      tags:
        - sharing_management
      description: Deletes the specified shared bucket.
      requestBody:
        content:
          application/json:
            schema: SharedBucketDeletionRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    shared_bucket_deletion_request = schemas.SharedBucketDeletionRequest().load(body)
    shared_bucket_deletion_entity = entities.SharedBucketDeletion(
        **shared_bucket_deletion_request
    )

    services.delete_shared_bucket(shared_bucket_deletion_entity)

    return {}, 200
