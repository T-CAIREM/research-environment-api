from marshmallow import Schema, fields, post_load


class BillingAccountSetup(Schema):
    email = fields.Str()
    billing_account_id = fields.Str()
