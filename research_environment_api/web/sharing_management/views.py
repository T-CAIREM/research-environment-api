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


@sharing_management_bp.post("/bucket/share")
def share_bucket():
    """Shares bucket.
    ---
    post:
      tags:
        - sharing_management
      description: Shares a bucket.
      requestBody:
        content:
          application/json:
            schema: ShareBucketRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    share_bucket_request = schemas.ShareBucketRequest().load(body)
    share_bucket_entity = entities.ShareBucket(**share_bucket_request)

    services.share_bucket_to(share_bucket_entity)

    return {}, 200


@sharing_management_bp.post("/bucket/revoke_access")
def revoke_access_to_shared_bucket():
    """Revokes a user's access to shared bucket.
    ---
    post:
      tags:
        - sharing_management
      description: Revokes a user's access to shared bucket.
      requestBody:
        content:
          application/json:
            schema: RevokeSharedBucketAccessRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    revoke_shared_bucket_access_request = (
        schemas.RevokeSharedBucketAccessRequest().load(body)
    )
    revoke_shared_bucket_access_entity = entities.RevokeSharedBucketAccess(
        **revoke_shared_bucket_access_request
    )

    services.revoke_access_to_shared_bucket(revoke_shared_bucket_access_entity)

    return {}, 200


@sharing_management_bp.post("/bucket/generate_signed_url")
def generate_signed_url():
    """Generate signed url for a shared bucket to upload files.
    ---
    post:
      tags:
        - sharing_management
      description: Generates signed url for a shared bucket to upload files.
      requestBody:
        content:
          application/json:
            schema: SignedUrlGenerationRequest
      responses:
        200:
          description: Returns a signed url.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    signed_url_generation_request = schemas.SignedUrlGenerationRequest().load(body)
    signed_url_generation_entity = entities.GenerateSignedUrl(
        **signed_url_generation_request
    )

    signed_url = services.generate_signed_url(signed_url_generation_entity)

    return {"signed_url": signed_url}, 200


@sharing_management_bp.get("/<bucket_name>")
def get_shared_bucket_content(bucket_name: str):
    """Get content of a directory inside GCP bucket.
    ---
    get:
      tags:
        - sharing_management
      description: Gets content of a directory inside GCP bucket.
      requestBody:
        content:
          application/json:
            schema: GetSharedBucketContentRequest
      responses:
        200:
          description: Returns bucket content.
          content:
            application/json:
              schema: SharedBucketObject
    """
    subdir = request.args.get("subdir") or ""
    get_shared_bucket_content_request = schemas.GetSharedBucketContentRequest().load(
        {"bucket_name": bucket_name, "subdir": subdir}
    )
    get_shared_bucket_content_entity = entities.GetSharedBucketContent(
        **get_shared_bucket_content_request
    )

    files_and_directories = services.get_shared_bucket_content(
        get_shared_bucket_content_entity
    )
    shared_bucket_objects = schemas.SharedBucketObject(many=True).dump(
        files_and_directories
    )
    return shared_bucket_objects, 200


@sharing_management_bp.post("/bucket/content/create")
def create_shared_bucket_directory():
    """Create a directory in a GCP bucket.
    ---
    post:
      tags:
        - sharing_management
      description: Creates a directory in a GCP bucket.
      requestBody:
        content:
          application/json:
            schema: CreateSharedBucketDirectoryRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    create_shared_bucket_directory_request = (
        schemas.CreateSharedBucketDirectoryRequest().load(body)
    )

    create_shared_bucket_directory_entity = entities.CreateSharedBucketDirectory(
        **create_shared_bucket_directory_request
    )

    services.create_shared_bucket_directory(create_shared_bucket_directory_entity)

    return {}, 200


@sharing_management_bp.post("/bucket/content/delete")
def delete_shared_bucket_content():
    """Delete shared bucket content.
    ---
    post:
      tags:
        - sharing_management
      description: Deletes shared bucket file or directory.
      requestBody:
        content:
          application/json:
            schema: DeleteSharedBucketContentRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    delete_shared_bucket_content_request = (
        schemas.DeleteSharedBucketContentRequest().load(body)
    )

    delete_shared_bucket_content_entity = entities.DeleteSharedBucketContent(
        **delete_shared_bucket_content_request
    )

    services.delete_shared_bucket_content(delete_shared_bucket_content_entity)

    return {}, 200
