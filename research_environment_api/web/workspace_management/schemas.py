from marshmallow import Schema, fields, validate

from research_environment_api.modules.workspace_management.enums import Region


class WorkspaceCreationRequest(Schema):
    region = fields.Str(
        required=True, validate=validate.OneOf([r.value for r in Region])
    )
    email = fields.Str(required=True, validate=validate.Email())
    billing_account_id = fields.Str(required=True)


class WorkspaceDeletionRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())
    workspace_id = fields.Str(required=True)


class ListActiveWorkspacesRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())


class Workbench(Schema):
    gcp_identifier = fields.Str(required=True)
    resource_status = fields.Str(required=True)
    dataset_slug = fields.Str(required=True)
    dataset_version = fields.Str(required=True)
    cpu = fields.Float(required=True)
    memory = fields.Float(required=True)
    url = fields.URL(required=True)


class Workspace(Schema):
    gcp_project_id = fields.Str(required=True)
    region = fields.Str(required=True)
    billing_account_id = fields.Str(required=True)
    workbenches = fields.Nested(Workbench, many=True)
