from marshmallow import Schema, fields, validate
from research_environment_api.modules.workspace_management.enums import Region


class WorkbenchCreationRequest(Schema):
    workbench_type = fields.Str(required=True)
    machine_type = fields.Str(required=True)
    workspace_project_id = fields.Str(required=True)
    dataset = fields.Str(required=True)
    user_email = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    region = fields.Str(
        required=True, validate=validate.OneOf([r.value for r in Region])
    )
    persistent_disk = fields.Str(required=True)
    gpu_accelerator = fields.Str()


class WorkbenchStartStopRequest(Schema):
    workbench_type = fields.Str(required=True)
    user_email = fields.Str(required=True)
    workspace_project_id = fields.Str(requried=True)
    workbench_resource_id = fields.Str(required=True)
    instance_zone = fields.Str()
