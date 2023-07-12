from marshmallow import Schema, fields, validate


class JupyterWorkbenchCreationRequest(Schema):
    machine_type = fields.Str(required=True)
    user_project_id = fields.Str(required=True)
    dataset = fields.Str(required=True)
    email_id = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    region = fields.Str(required=True)
    persistent_disk = fields.Str(required=True)
    vm_image = fields.Str(required=True)
    gpu_accelerator = fields.Str(required=True)


class RstudioWorkbenchCreationRequest(Schema):
    machine_type = fields.Str(required=True)
    user_project_id = fields.Str(required=True)
    dataset = fields.Str(required=True)
    email_id = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    region = fields.Str(required=True)
    persistent_disk = fields.Str(required=True)
    gpu_accelerator = fields.Str(required=True)
