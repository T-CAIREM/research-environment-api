from marshmallow import Schema, fields, validate


class WorkbenchCreationRequest(Schema):
    workbench_type = fields.Str(required=True)
    machine_type = fields.Str(required=True)
    workspace_project_id = fields.Str(required=True)
    dataset = fields.Str(required=True)
    email_id = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    region = fields.Str(required=True)
    persistent_disk = fields.Str(required=True)
    gpu_accelerator = fields.Str()


class WorkbenchStopRequest(Schema):
    workbench_type = fields.Str(required=True)
    user_email = fields.Str(required=True)
    workspace_project_id = fields.Str(requried=True)
    workbench_resource_id = fields.Str(required=True)
    zone = fields.Str()
