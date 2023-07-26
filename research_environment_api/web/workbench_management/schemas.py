from marshmallow import Schema, fields, validate


class WorkbenchCreationRequest(Schema):
    workbench_type = fields.Str(required=True)
    machine_type = fields.Str(required=True)
    workspace_project_id = fields.Str(required=True)
    dataset_identifier = fields.Str(required=True)
    user_email = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    region = fields.Str(required=True)
    persistent_disk = fields.Str(required=True)
    gpu_accelerator_type = fields.Str()


class WorkbenchStopRequest(Schema):
    workbench_type = fields.Str(required=True)
    user_email = fields.Str(required=True)
    workspace_project_id = fields.Str(requried=True)
    workbench_resource_id = fields.Str(required=True)
    zone = fields.Str()


class WorkbenchUpdateRequest(Schema):
    workbench_type = fields.Str(required=True)
    machine_type = fields.Str(required=True)
    workbench_resource_id = fields.Str(required=True)
    workspace_project_id = fields.Str(requried=True)
    dataset_identifier = fields.Str(required=True)
    user_email = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    region = fields.Str(required=True)
    persistent_disk = fields.Str(required=True)
    vm_image = fields.Str(required=True)
    gpu_accelerator_type = fields.Str(required=True)
