from marshmallow import Schema, fields, validate
from marshmallow_oneofschema import OneOfSchema

from research_environment_api.modules.workbench_management.entities import (
    Region,
    Workbench,
)

from research_environment_api.modules.workspace_management.entities import (
    WorkspaceStatus,
)
from research_environment_api.web.workbench_management.schemas import Workbench as WorkbenchSchema
from research_environment_api.web.sharing_management.schemas import SharedBucket


class WorkspaceCreationRequest(Schema):
    region = fields.Enum(Region, by_value=True, required=True)
    user_email = fields.Str(required=True, validate=validate.Email())
    billing_account_id = fields.Str(required=True)


class WorkspaceDeletionRequest(WorkspaceCreationRequest):
    workspace_project_id = fields.Str(required=True)


class ListActiveWorkspacesRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())


class EntityScaffolding(Schema):
    id = fields.Str(required=True)
    status = fields.Str(required=True)
    gcp_project_id = fields.Str(required=True)


class EntityScaffoldingWorkbenchSchema(OneOfSchema):
    type_schemas = {"Workbench": WorkbenchSchema, "EntityScaffolding": EntityScaffolding}


class BillingInfo(Schema):
    billing_account_id = fields.Str(required=True)
    billing_enabled = fields.Boolean(required=True)


class Workspace(Schema):
    gcp_project_id = fields.Str(required=True)
    region = fields.Enum(Region, by_value=True, required=True)
    billing_info = fields.Nested(BillingInfo, required=True)
    workbenches = fields.Nested(EntityScaffoldingWorkbenchSchema, many=True)
    status = fields.Enum(WorkspaceStatus, by_value=True, required=True)


class SharedWorkspaceCreationRequest(Schema):
    user_email = fields.Str(required=True, validate=validate.Email())
    billing_account_id = fields.Str(required=True)


class SharedWorkspaceDeletionRequest(SharedWorkspaceCreationRequest):
    workspace_project_id = fields.Str(required=True)


class ListActiveSharedWorkspacesRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())


class SharedWorkspace(Schema):
    gcp_project_id = fields.Str(required=True)
    billing_info = fields.Nested(BillingInfo, required=True)
    buckets = fields.Nested(SharedBucket, many=True)
    status = fields.Enum(WorkspaceStatus, by_value=True, required=True)


class EntityScaffoldingWorkspaceSchema(OneOfSchema):
    type_schemas = {
        "Workspace": Workspace,
        "EntityScaffolding": EntityScaffolding,
        "SharedWorkspace": SharedWorkspace,
    }


class WorkspaceWorkflowIdentifier(Schema):
    workflow_id = fields.Str(required=True)
