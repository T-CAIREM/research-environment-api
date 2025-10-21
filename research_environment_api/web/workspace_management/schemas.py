from marshmallow import Schema, fields, validate
from marshmallow_oneofschema import OneOfSchema

from research_environment_api.modules.workbench_management.entities import (
    Region,
    Workbench,
)

from research_environment_api.modules.workspace_management.entities import (
    WorkspaceStatus,
)
from research_environment_api.web.workbench_management.schemas import (
    Workbench as WorkbenchSchema,
)
from research_environment_api.web.sharing_management.schemas import SharedBucket


class BaseWorkspaceSchema(Schema):
    user_email = fields.Str(required=True, validate=validate.Email())
    billing_account_id = fields.Str(required=True)


class WorkspaceCreationRequest(BaseWorkspaceSchema):
    user_groups = fields.List(fields.Str(), required=True)


class WorkspaceDeletionRequest(BaseWorkspaceSchema):
    workspace_project_id = fields.Str(required=True)


class ListActiveWorkspacesRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())


class EntityScaffolding(Schema):
    gcp_identifier = fields.Str(required=True, attribute="id")
    status = fields.Str(required=True)
    gcp_project_id = fields.Str(required=True)


class EntityScaffoldingWorkbenchSchema(OneOfSchema):
    type_schemas = {
        "Workbench": WorkbenchSchema,
        "EntityScaffolding": EntityScaffolding,
    }


class ServiceErrorSchema(Schema):
    error_type = fields.Str(required=True)
    message = fields.Str(required=True)
    resource_id = fields.Str(required=True)
    service_name = fields.Str(required=True)
    details = fields.Str(missing=None, allow_none=True)
    can_retry = fields.Bool(missing=False)


class BillingInfo(Schema):
    billing_account_id = fields.Str(required=True)
    billing_enabled = fields.Boolean(required=True)


class Workspace(Schema):
    gcp_project_id = fields.Str(required=True)
    billing_info = fields.Nested(BillingInfo, required=True)
    workbenches = fields.Nested(EntityScaffoldingWorkbenchSchema, many=True)
    status = fields.Enum(WorkspaceStatus, by_value=True, required=True)
    is_owner = fields.Bool(required=True)
    service_errors = fields.Nested(ServiceErrorSchema, many=True, missing=[])
    is_accessible = fields.Bool(required=True)
    access_denial_reason = fields.Str(allow_none=True, missing=None)


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
    is_owner = fields.Boolean(required=True)
    service_errors = fields.Nested(ServiceErrorSchema, many=True, missing=[])
    is_accessible = fields.Bool(required=True)
    access_denial_reason = fields.Str(allow_none=True, missing=None)


class EntityScaffoldingWorkspaceSchema(OneOfSchema):
    type_schemas = {
        "Workspace": Workspace,
        "EntityScaffolding": EntityScaffolding,
        "SharedWorkspace": SharedWorkspace,
    }


class WorkspaceWorkflowIdentifier(Schema):
    workflow_id = fields.Str(required=True)


class ListWorkspaceQuotasRequest(Schema):
    workspace_project_id = fields.Str(required=True)


class UpdateWorkspaceBillingAccountRequest(Schema):
    workspace_project_id = fields.Str(required=True)
    billing_account_id = fields.Str(required=True)


class QuotaInfoSchema(Schema):
    metric_name = fields.Str(required=True)
    limit = fields.Int(required=True)
    usage = fields.Int(required=True)
    region = fields.Str(required=True)
