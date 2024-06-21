from marshmallow import Schema, fields


class TimestampTuple(Schema):
    created_at = fields.DateTime(required=True)
    deleted_at = fields.DateTime()


class WorkbenchMonitoringDataEntry(Schema):
    user_email = fields.Str(required=True)
    dataset_identifier = fields.Str(required=True)
    instance_type = fields.Str(required=True)
    timestamps = fields.Nested(TimestampTuple, many=True)
    total_time = fields.Str(required=True)
