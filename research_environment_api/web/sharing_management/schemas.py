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
