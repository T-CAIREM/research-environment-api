from marshmallow import Schema, fields, validate

from research_environment_api.modules.workbench_management.entities import (
    WorkbenchStatus,
    WorkbenchType,
)
from research_environment_api.modules.workspace_management.enums import Region


class WorkspaceCreationRequest(Schema):
    region = fields.Str(
        required=True, validate=validate.OneOf([r.value for r in Region])
    )
    email_id = fields.Str(required=True, validate=validate.Email())
    billing_account_id = fields.Str(required=True)


class WorkspaceDeletionRequest(Schema):
    email_id = fields.Str(required=True, validate=validate.Email())
    billing_account_id = fields.Str(required=True)
    region = fields.Str(
        required=True, validate=validate.OneOf([r.value for r in Region])
    )
    workspace_id = fields.Str(required=True)


class ListActiveWorkspacesRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())


class Workbench(Schema):
    gcp_identifier = fields.Str(required=True)
    status = fields.Enum(WorkbenchStatus, by_value=True, required=True)
    dataset_identifier = fields.Str(required=True)
    cpu = fields.Float(required=True)
    memory = fields.Float(required=True)
    url = fields.URL(required=True)
    type = fields.Enum(WorkbenchType, by_value=True, required=True)
    zone = fields.Str()


class Workspace(Schema):
    gcp_project_id = fields.Str(required=True)
    region = fields.Enum(Region, by_value=True, required=True)
    billing_account_id = fields.Str(required=True)
    workbenches = fields.Nested(Workbench, many=True)
