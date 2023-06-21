from marshmallow import Schema, fields, validate

from research_environment_api.modules.workspace_management.enums import Region


class WorkspaceCreationRequest(Schema):
    region = fields.Str(
        required=True, validate=validate.OneOf([r.value for r in Region])
    )
    email = fields.Str(required=True)
    billing_account_id = fields.Str(required=True)


class WorkspaceDeletionRequest(Schema):
    gcp_project_id = fields.Str(required=True)


class ListActiveWorkspacesRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())
