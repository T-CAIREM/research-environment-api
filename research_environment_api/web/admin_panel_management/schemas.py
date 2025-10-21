from marshmallow import Schema, fields


class TaskResultSchema(Schema):
    """Schema for serializing TaskResult entities"""
    value = fields.Str(allow_none=True)
    error = fields.String(allow_none=True)
    traceback = fields.String(allow_none=True)


class TaskSchema(Schema):
    """Schema for serializing Task entities"""
    id = fields.String(required=True)
    name = fields.String(allow_none=True)
    args = fields.List(fields.Str(), allow_none=True)
    kwargs = fields.Dict(keys=fields.Str(), values=fields.Str(), allow_none=True)
    status = fields.String(allow_none=True)
    worker = fields.String(allow_none=True)
    eta = fields.String(allow_none=True)
    date_done = fields.DateTime(allow_none=True)
    result = fields.Nested(TaskResultSchema, allow_none=True)
    ready = fields.Boolean()
    successful = fields.Boolean()
    failed = fields.Boolean()


class TaskOperationResultSchema(Schema):
    """Schema for serializing TaskOperationResult entities"""
    task_id = fields.String(required=True)
    task_type = fields.String(allow_none=True)
    worker = fields.String(allow_none=True)
    operations = fields.Dict()


class WorkerStatsSchema(Schema):
    """Schema for serializing WorkerStats entities"""
    name = fields.String(required=True)
    stats = fields.Dict()
    active_tasks = fields.Integer()
    registered_tasks = fields.List(fields.String())
