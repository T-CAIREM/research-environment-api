from marshmallow import Schema, fields


class WorkbenchMonitoringDataEntry(Schema):
    user_email = fields.Str(required=True)
    dataset_identifier = fields.Str(required=True)
    instance_type = fields.Str(required=True)
    total_time = fields.Str(required=True)


class UsersPerDatasetEntry(Schema):
    dataset_identifier = fields.Str(required=True)
    user_emails = fields.List(fields.Str(), required=True)
