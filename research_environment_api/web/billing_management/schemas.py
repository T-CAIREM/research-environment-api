from marshmallow import Schema, fields, validate


class ListBillingAccountsRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())


class BillingAccount(Schema):
    display_name = fields.Str(required=True)
    resource_name = fields.Str(required=True, attribute="name")
