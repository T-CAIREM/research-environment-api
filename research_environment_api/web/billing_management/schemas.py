from marshmallow import Schema, fields, validate


class ListBillingAccountsRequest(Schema):
    email = fields.Str(required=True, validate=validate.Email())


class ShareBillingAccountRequest(Schema):
    owner_email = fields.Str(required=True, validate=validate.Email())
    user_email = fields.Str(required=True, validate=validate.Email())
    resource_name = fields.Str(required=True)


class RevokeBillingAccountAccessRequest(Schema):
    owner_email = fields.Str(required=True, validate=validate.Email())
    user_email = fields.Str(required=True, validate=validate.Email())
    resource_name = fields.Str(required=True)


class BillingAccount(Schema):
    id = fields.Str(required=True)
    is_owner = fields.Bool(required=True)
