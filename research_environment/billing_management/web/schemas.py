from marshmallow import Schema, fields, post_load

from billing_management.core import entities


class BillingAccountCreation(Schema):
    cloud_identity_id = fields.Str()
    billing_account_number = fields.Str()

    @post_load
    def make_billing_account(self, data, **kwargs):
        return entities.BillingAccount(
            cloud_identity_id=data["cloud_identity_id"],
            account_number=data["billing_account_number"],
        )


class CreatedBillingAccount(Schema):
    cloud_identity_id = fields.Str()
    billing_account_id = fields.Str()
    billing_account_number = fields.Str()
