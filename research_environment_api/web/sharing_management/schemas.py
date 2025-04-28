import string

from marshmallow import Schema, fields, validate

from research_environment_api.modules.workbench_management.entities import (
    Region,
)

from research_environment_api.modules.sharing_management.enums import BucketPermissions


class SharedBucketCreationRequest(Schema):
    region = fields.Enum(Region, by_value=True, required=True)
    workspace_project_id = fields.Str(required=True)
    user_email = fields.Str(required=True, validate=validate.Email())
    user_defined_bucket_name = fields.Str(
        required=True,
        validate=[
            validate.ContainsOnly(string.ascii_lowercase + string.digits + "-_"),
            validate.Length(min=1, max=32),
        ],
    )


class SharedBucketDeletionRequest(Schema):
    bucket_name = fields.Str(required=True)


class ShareBucketRequest(Schema):
    sharer_email = fields.Str(required=True)
    project_id = fields.Str(required=True)
    accessor_email = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    permissions = fields.Enum(BucketPermissions, required=True, by_value=True)


class RevokeSharedBucketAccessRequest(Schema):
    sharer_email = fields.Str(required=True)
    accessor_email = fields.Str(required=True)
    bucket_name = fields.Str(required=True)


class SharedBucket(Schema):
    bucket_name = fields.Str(required=True)
    is_owner = fields.Bool(required=True)
    is_admin = fields.Bool(required=True)


class SignedUrlGenerationRequest(Schema):
    filename = fields.Str(required=True)
    size = fields.Int(
        required=True, validate=validate.Range(min=0, min_inclusive=False)
    )
    bucket_name = fields.Str(required=True)
    user_email = fields.Str(required=True, validate=validate.Email())


class GetSharedBucketContentRequest(Schema):
    bucket_name = fields.Str(required=True)
    subdir = fields.Str(required=True)
    user_email = fields.Str(required=True, validate=validate.Email())


class CreateSharedBucketDirectoryRequest(Schema):
    bucket_name = fields.Str(required=True)
    parent_path = fields.Str(
        required=True,
        validate=validate.Regexp(regex=".*/$|^$", error="Not a directory"),
    )
    directory_name = fields.Str(required=True)
    user_email = fields.Str(required=True, validate=validate.Email())


class DeleteSharedBucketContentRequest(Schema):
    bucket_name = fields.Str(required=True)
    full_path = fields.Str(required=True)
    user_email = fields.Str(required=True, validate=validate.Email())


class SharedBucketObject(Schema):
    type = fields.Str(required=True)
    name = fields.Str(required=True)
    full_path = fields.Str(required=True)
    size = fields.Str()
    modification_time = fields.Str()


class BucketAccessRequestCreationRequest(Schema):
    accesor_email = fields.Str(required=True, validate=validate.Email())
    bucket_name = fields.Str(required=True)
    project_id = fields.Str(required=True)
    requested_permissions = fields.Enum(
        BucketPermissions, required=True, by_value=True
    )

class BucketAccessRequestDecisionRequest(Schema):
    request_id = fields.Int(required=True)
    sharer_email = fields.Str(required=True, validate=validate.Email())
    bucket_name = fields.Str(required=True)
    project_id = fields.Str(required=True)


class PendingBucketAccessRequest(Schema):
    request_id = fields.Int(required=True)
    accesor_email = fields.Str(required=True, validate=validate.Email())
    bucket_name = fields.Str(required=True)
    requested_permissions = fields.Enum(
        BucketPermissions, required=True, by_value=True
    )
