from marshmallow import Schema, fields, validate


class TaskResultSchema(Schema):
    value = fields.Str(allow_none=True)
    error = fields.String(allow_none=True)
    traceback = fields.String(allow_none=True)


class TaskSchema(Schema):
    id = fields.String(required=True)
    name = fields.String(allow_none=True)
    args = fields.List(fields.Str(), allow_none=True)
    kwargs = fields.Dict(keys=fields.Str(), values=fields.Str(), allow_none=True)
    status = fields.String(allow_none=True)
    worker = fields.String(allow_none=True)
    eta = fields.String(allow_none=True)
    date_done = fields.DateTime(allow_none=True)
    result = fields.Nested(TaskResultSchema, allow_none=True)


class TaskOperationResultSchema(Schema):
    task_id = fields.String(required=True)
    task_type = fields.String(allow_none=True)
    worker = fields.String(allow_none=True)
    operations = fields.Dict()


class WorkerStatsSchema(Schema):
    name = fields.String(required=True)
    stats = fields.Dict()
    active_tasks = fields.Integer()
    registered_tasks = fields.List(fields.String())


class WorkbenchActivitiesQueryParams(Schema):
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=20, validate=validate.Range(min=1, max=100))
    q = fields.Str(missing="", allow_none=True)
    status = fields.Str(allow_none=True)
    build_type = fields.Str(allow_none=True)
    workspace_id = fields.Str(allow_none=True)
    workbench_id = fields.Str(allow_none=True)
    email = fields.Str(allow_none=True)
    sort_by = fields.Str(
        missing="id",
        validate=validate.OneOf(
            [
                "id",
                "invoker_email",
                "workbench_id",
                "build_type",
                "build_status",
                "workspace_id",
            ]
        ),
    )
    sort_direction = fields.Str(
        missing="desc", validate=validate.OneOf(["asc", "desc"])
    )


class WorkbenchActivitySchema(Schema):
    id = fields.UUID(required=True)
    invoker_email = fields.Str(allow_none=True)
    workbench_id = fields.Str(allow_none=True)
    build_type = fields.Str(allow_none=True)
    build_status = fields.Str(allow_none=True)
    workspace_id = fields.Str(allow_none=True)
    build_error_information = fields.Str(allow_none=True)


class WorkbenchActivitiesSummarySchema(Schema):
    total = fields.Int(required=True)
    recent = fields.Int(required=True)
    by_build_type = fields.Dict(keys=fields.Str(), values=fields.Int())
    by_status = fields.Dict(keys=fields.Str(), values=fields.Int())


class WorkbenchActivityStatusUpdateRequest(Schema):
    activity_ids = fields.List(
        fields.UUID(), required=True, validate=validate.Length(min=1)
    )
    new_status = fields.Str(required=True)
