"""
Schemas for Celery management API endpoints
"""
from marshmallow import Schema, fields


class TaskResultSchema(Schema):
    """Schema for serializing TaskResult entities"""
    value = fields.Raw(allow_none=True)
    error = fields.String(allow_none=True)
    traceback = fields.String(allow_none=True)


class TaskSchema(Schema):
    """Schema for serializing Task entities"""
    id = fields.String(required=True)
    name = fields.String(allow_none=True)
    args = fields.List(fields.Raw(), allow_none=True)
    kwargs = fields.Dict(allow_none=True)
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


class BatchOperationResultSchema(Schema):
    """Schema for serializing BatchOperationResult entities"""
    total_matched = fields.Integer()
    total_processed = fields.Integer()
    limited = fields.Boolean()
    pattern = fields.String(allow_none=True)
    tasks = fields.List(fields.Nested(TaskOperationResultSchema))
    errors = fields.List(fields.String())


class WorkerStatsSchema(Schema):
    """Schema for serializing WorkerStats entities"""
    name = fields.String(required=True)
    stats = fields.Dict()
    active_tasks = fields.Integer()
    registered_tasks = fields.List(fields.String())


# Request schemas
class TaskSearchRequestSchema(Schema):
    """Schema for task search requests"""
    name_fragment = fields.String(required=True)


class TaskFilterRequestSchema(Schema):
    """Schema for task filtering requests"""
    status = fields.String(allow_none=True)
    task_type = fields.String(allow_none=True)
    worker = fields.String(allow_none=True)


class BackendTasksRequestSchema(Schema):
    """Schema for listing backend tasks requests"""
    limit = fields.Integer(load_default=100)
    pattern = fields.String(allow_none=True)


class DeleteTaskPatternRequestSchema(Schema):
    """Schema for deleting tasks by pattern requests"""
    pattern = fields.String(required=True)
    use_glob = fields.Boolean(load_default=False)
    limit = fields.Integer(load_default=100)
