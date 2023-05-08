from marshmallow import Schema, fields, validate

from research_environment_api.modules.workspace_management.enums import Region


class WorkspaceCreationRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())
    region = fields.Str(
        required=True, validate=validate.OneOf([r.value for r in Region])
    )
    billing_account_resource_name = fields.Str(required=True)
