from marshmallow import Schema, fields


class IdentityProvisioningRequest(Schema):
    user_name = fields.Str(required=True)
    password = fields.Str(required=True)
    recovery_email = fields.Str(required=True)
    family_name = fields.Str(required=True)
    given_name = fields.Str(required=True)


class ProvisionedIdentity(Schema):
    email = fields.Str(required=True)
    recovery_email = fields.Str(required=True)
    family_name = fields.Str(required=True)
    given_name = fields.Str(required=True)
