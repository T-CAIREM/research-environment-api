from marshmallow import Schema, fields

from research_environment_api.modules.workbench_management.entities import (
    MachineType,
    WorkbenchType,
    Region,
)

from research_environment_api.modules.workbench_management.entities import (
    WorkbenchStatus,
)


class WorkbenchBase(Schema):
    workbench_type = fields.Enum(WorkbenchType, by_value=True, required=True)
    workspace_project_id = fields.Str(required=True)
    user_email = fields.Str(required=True)


class WorkbenchCreateRequest(WorkbenchBase):
    dataset_identifier = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    machine_type = fields.Enum(MachineType, by_value=True, required=True)
    memory = fields.Float(required=True)
    cpu = fields.Int(required=True)
    disk_size = fields.Int(required=True)
    user_groups = fields.List(fields.Str(), required=True)
    gpu_accelerator_type = fields.Str(allow_none=True)
    sharing_bucket_identifiers = fields.List(fields.Str())
    collaborators = fields.List(fields.Str(), allow_none=True)
    region = fields.Enum(Region, by_value=True, required=True)


class WorkbenchToggleStateRequest(WorkbenchBase):
    workbench_resource_id = fields.Str(required=True)


class WorkbenchUpdateRequest(WorkbenchBase):
    workbench_resource_id = fields.Str(required=True)
    machine_type = fields.Enum(MachineType, by_value=True, required=True)


class WorkbenchDestroyRequest(WorkbenchBase):
    workbench_resource_id = fields.Str(required=True)


class Workbench(Schema):
    gcp_identifier = fields.Str(required=True, attribute="id")
    status = fields.Enum(WorkbenchStatus, by_value=True, required=True)
    dataset_identifier = fields.Str(required=True)
    cpu = fields.Int(required=True)
    memory = fields.Float(required=True)
    disk_size = fields.Int(required=True)
    machine_type = fields.Enum(MachineType, by_value=True, required=True)
    url = fields.URL(required=True)
    workbench_type = fields.Enum(
        WorkbenchType, by_value=True, required=True, attribute="type"
    )
    zone = fields.Str()
    region = fields.Enum(Region, by_value=True, required=True)
    sharing_bucket_identifiers = fields.List(fields.Str())
    collaborators = fields.List(fields.Str(), allow_none=True)
    service_account_name = fields.Str(required=True)
    workbench_owner_username = fields.Str(required=False)


class WorkbenchWorkflowIdentifier(Schema):
    workflow_id = fields.Str(required=True)


class WorkbenchCollaboratorModificationRequest(Schema):
    service_account_name = fields.Str(required=True)
    workspace_project_id = fields.Str(required=True)
    collaborators = fields.List(fields.Email(), required=True)


class WorkbenchCollaboratorList(Schema):
    collaborators = fields.List(fields.Email(), required=True)


class WorkbenchNotificationRequest(Schema):
    service_account_name = fields.Str(required=True)
    workspace_project_id = fields.Str(required=True)


class WorkbenchNotification(Schema):
    id = fields.UUID(required=True)
    email = fields.Email(required=True)
    timestamp = fields.Str(required=True)


class WorkbenchNotificationList(Schema):
    notifications = fields.List(fields.Nested(WorkbenchNotification), required=True)
