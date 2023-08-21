from marshmallow import Schema, fields, validate

from research_environment_api.modules.workbench_management.entities import (
    MachineType,
    Region,
    WorkbenchStatus,
    WorkbenchType,
)
from research_environment_api.web.workflow.schemas import Workflow
from marshmallow_oneofschema import OneOfSchema


class WorkspaceCreationRequest(Schema):
    region = fields.Enum(Region, by_value=True, required=True)
    user_email = fields.Str(required=True, validate=validate.Email())
    billing_account_id = fields.Str(required=True)


class WorkspaceDeletionRequest(WorkspaceCreationRequest):
    workspace_project_id = fields.Str(required=True)


class ListActiveWorkspacesRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())


class Workbench(Schema):
    gcp_identifier = fields.Str(required=True)
    status = fields.Enum(WorkbenchStatus, by_value=True, required=True)
    dataset_identifier = fields.Str(required=True)
    cpu = fields.Float(required=True)
    memory = fields.Float(required=True)
    disk_size = fields.Int(required=True)
    machine_type = fields.Enum(MachineType, by_value=True, required=True)
    url = fields.URL(required=True)
    workbench_type = fields.Enum(
        WorkbenchType, by_value=True, required=True, attribute="type"
    )
    zone = fields.Str()
    workflow_in_progress = fields.Nested(Workflow)


class EntityScaffolding(Schema):
    id = fields.str(required=True)
    gcp_project_id = fields.Str(required=True)


class EntityScaffoldingWorkbenchSchema(OneOfSchema):
    type_schemas = {"Workbench": Workbench, "EntityScaffolding": EntityScaffolding}


class BillingInfo(Schema):
    billing_account_id = fields.Str(required=True)
    billing_enabled = fields.Boolean(required=True)


class Workspace(Schema):
    gcp_project_id = fields.Str(required=True)
    region = fields.Enum(Region, by_value=True, required=True)
    billing_info = fields.Nested(BillingInfo, required=True)
    workbenches = fields.Nested(EntityScaffoldingWorkbenchSchema, many=True)
    workflow_in_progress = fields.Nested(Workflow)


class EntityScaffoldingWorkspaceSchema(OneOfSchema):
    type_schemas = {"Workspace": Workspace, "EntityScaffolding": EntityScaffolding}
