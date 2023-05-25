from marshmallow import Schema, fields, validate


class IdentityProvisioningRequest(Schema):
    user_name = fields.Str(required=True)
    password = fields.Str(required=True)
    recovery_email = fields.Str(required=True, validate=validate.Email())
    family_name = fields.Str(required=True)
    given_name = fields.Str(required=True)


class ProvisionedIdentity(Schema):
    primary_email = fields.Str(required=True)
    recovery_email = fields.Str(required=True, validate=validate.Email())
    family_name = fields.Str(required=True)
    given_name = fields.Str(required=True)
