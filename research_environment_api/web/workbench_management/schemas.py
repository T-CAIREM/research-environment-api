from marshmallow import Schema, fields, validate
from research_environment_api.modules.workspace_management.enums import Region


class WorkbenchBaseClass(Schema):
    workbench_type = fields.Str(required=True)
    workspace_project_id = fields.Str(required=True)


class WorkbenchCreateDestroyRequest(WorkbenchBaseClass):
    machine_type = fields.Str(required=True)
    workspace_project_id = fields.Str(required=True)
    dataset = fields.Str(required=True)
    user_email = fields.Str(required=True)
    dataset_identifier = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    region = fields.Enum(Region, by_value=True, required=True)
    persistent_disk = fields.Str(required=True)
    gpu_accelerator_type = fields.Str()


class WorkbenchStartStopRequest(WorkbenchBaseClass):
    user_email = fields.Str(required=True)
    workbench_resource_id = fields.Str(required=True)
    instance_zone = fields.Str()


class WorkbenchUpdateRequest(WorkbenchCreateDestroyRequest):
    workbench_resource_id = fields.Str(required=True)
