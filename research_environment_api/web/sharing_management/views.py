from flask import request

from research_environment_api.modules.sharing_management import entities, services
from research_environment_api.web.sharing_management import (
    sharing_management_bp,
    schemas,
)
from research_environment_api.web.decorators import validate_token


@sharing_management_bp.post("/bucket/create")
@validate_token
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
@validate_token
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
@validate_token
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


@sharing_management_bp.post("/bucket/request_access")
@validate_token
def request_bucket_access():
    """Request access to a bucket.
    ---
    post:
      tags:
        - sharing_management
      description: Submits a request for access to a shared bucket.
      requestBody:
        content:
          application/json:
            schema: BucketAccessRequestCreationRequest
      responses:
        201:
          description: Access request created successfully.
          content:
            application/json:
              schema:
        400:
          description: Invalid request, bucket doesn't exist, user already has access,
                       or a pending request already exists.
    """
    body = request.get_json()
    access_request = schemas.BucketAccessRequestCreationRequest().load(body)
    access_request_entity = entities.BucketAccessRequestCreation(**access_request)

    services.request_bucket_access(access_request_entity)

    return {}, 201


@sharing_management_bp.get("/bucket/pending_requests")
@validate_token
def list_pending_access_requests():
    """List pending access requests for buckets owned/administered by the user.
    ---
    get:
      tags:
        - sharing_management
      description: Lists all pending bucket access requests for buckets where the user is an owner or admin.
      parameters:
        - name: admin_email
          in: query
          required: true
          schema:
            type: string
      responses:
        200:
          description: List of pending requests.
          content:
            application/json:
              schema:
                type: array
                items: PendingBucketAccessRequest
    """
    admin_email = request.args.get("admin_email")
    if not admin_email:
        return {"error": "admin_email query parameter is required"}, 400

    list_filter = entities.ListPendingRequests(admin_email=admin_email)
    pending_requests = services.list_pending_access_requests(list_filter)
    
    return schemas.PendingBucketAccessRequest(many=True).dump(pending_requests), 200


@sharing_management_bp.patch("/bucket/request_access/")
@validate_token
def bucket_access_request_response():
    """Approve a bucket access request.
    ---
    patch:
      tags:
        - sharing_management
      description: Approves a pending bucket access request.
      requestBody:
        content:
          application/json:
            schema: BucketAccessRequestDecisionRequest
      responses:
        200:
          description: Request approved successfully.
          content:
            application/json:
              schema: BucketAccessRequestDecisionResponse
        400:
          description: Request not found or already processed.
        403:
          description: Insufficient permissions to approve request.
    """
    body = request.get_json()
    decision_request = schemas.BucketAccessRequestDecisionRequest().load(body)
    decision_entity = entities.BucketAccessRequestDecision(**decision_request)

    services.approve_bucket_access_request(decision_entity)

    return schemas.BucketAccessRequestDecisionResponse().dump(decision_entity), 200


@sharing_management_bp.post("/bucket/revoke_access")
@validate_token
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
@validate_token
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
@validate_token
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
    user_email = request.args.get("user_email")
    get_shared_bucket_content_request = schemas.GetSharedBucketContentRequest().load(
        {"bucket_name": bucket_name, "subdir": subdir, "user_email": user_email}
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
@validate_token
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


@sharing_management_bp.delete("/bucket/content/delete")
@validate_token
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


