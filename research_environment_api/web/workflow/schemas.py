from marshmallow import Schema, fields
from research_environment_api.background.enums import BuildType, WorkflowStatus


class Workflow(Schema):
    id = fields.Str(required=True)
    build_type = fields.Enum(BuildType, by_value=True, required=True)
    status = fields.Enum(WorkflowStatus, by_value=True, required=True, attribute="build_status")
    error = fields.Str(required=False, attribute="build_error_information")
