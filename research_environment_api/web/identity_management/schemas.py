from marshmallow import Schema, fields


class IdentityProvisioningRequest(Schema):
    user_name = fields.Str()
    password = fields.Str()
    recovery_email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()


class ProvisionedIdentity(Schema):
    email = fields.Str()
    recovery_email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()
