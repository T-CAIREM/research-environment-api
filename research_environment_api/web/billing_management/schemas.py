from marshmallow import Schema, fields


class ListBillingAccountsRequest(Schema):
    email = fields.Str(required=True)


class BillingAccount(Schema):
    display_name = fields.Str(required=True)
    resource_name = fields.Str(required=True, attribute="name")
