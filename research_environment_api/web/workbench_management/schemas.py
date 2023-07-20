from marshmallow import Schema, fields, validate


class WorkbenchCreationRequest(Schema):
    invoker_username = fields.Str(required=True)
    workbench_type = fields.Str(required=True)
    machine_type = fields.Str(required=True)
    user_project_id = fields.Str(required=True)
    dataset = fields.Str(required=True)
    email_id = fields.Str(required=True)
    bucket_name = fields.Str(required=True)
    region = fields.Str(required=True)
    persistent_disk = fields.Str(required=True)
    gpu_accelerator = fields.Str()


class JupyterWorkbenchStopRequest(Schema):
    invoker_username = fields.Str(required=True)
    user_project = fields.Str(requried=True)
    instance_name = fields.Str(required=True)
    gcp_identifier = fields.Str(required=True)
