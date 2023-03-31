from marshmallow import Schema, fields, post_load

from billing_management.core import entities


class BillingAccountCreation(Schema):
    cloud_identity_id = fields.Str()
    billing_account_number = fields.Str()

    @post_load
    def make_billing_account(self, data, **kwargs):
        return entities.BillingAccount(**data)


class BillingAccount(Schema):
    cloud_identity_id = fields.Str()
    billing_account_id = fields.Str()
    billing_account_number = fields.Str()
