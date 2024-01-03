from marshmallow import Schema, fields, validate

from research_environment_api.modules.workbench_management.entities import (
    Region,
)


class SharedBucketCreationRequest(Schema):
    region = fields.Enum(Region, by_value=True, required=True)
    workspace_project_id = fields.Str(required=True)
    user_email = fields.Str(required=True, validate=validate.Email())


class SharedBucketDeletionRequest(Schema):
    bucket_name = fields.Str(required=True)


class ShareBucketRequest(Schema):
    sharer_email = fields.Str(required=True)
    project_id = fields.Str(required=True)
    accessor_email = fields.Str(required=True)
    bucket_name = fields.Str(required=True)


class RevokeSharedBucketAccessRequest(Schema):
    sharer_email = fields.Str(required=True)
    accessor_email = fields.Str(required=True)
    bucket_name = fields.Str(required=True)


class SharedBucket(Schema):
    bucket_name = fields.Str(required=True)
    is_owner = fields.Bool(required=True)


class SignedUrlGenerationRequest(Schema):
    filename = fields.Str(required=True)
    size = fields.Int(required=True, validate=validate.Range(min=0, min_inclusive=False))
    bucket_name = fields.Str(required=True)
