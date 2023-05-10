from marshmallow import Schema, fields, validate

from research_environment_api.modules.workspace_management.enums import Region


class WorkspaceCreationRequest(Schema):
    region = fields.Str(
        required=True, validate=validate.OneOf([r.value for r in Region])
    )
    family_name = fields.Str(required=True)
    billing_account_resource_name = fields.Str(required=True)


class ListActiveWorkspacesRequest(Schema):
    family_name = fields.Str(required=True)
