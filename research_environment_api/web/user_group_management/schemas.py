from marshmallow import Schema, fields


class UserGroupCreationRequest(Schema):
    group_name = fields.Str(required=True)
    description = fields.Str(required=True)
