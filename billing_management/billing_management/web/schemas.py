from marshmallow import Schema, fields, post_load


class BillingAccountCreation(Schema):
    clout_identity_id = fields.Str()
    billing_account_number = fields.Str()


class BillingAccount(Schema):
    billing_account_id = fields.Str()
    billing_account_number = fields.Str()
    clout_identity_id = fields.Str()
