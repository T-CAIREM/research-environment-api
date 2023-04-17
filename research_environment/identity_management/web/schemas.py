from marshmallow import Schema, fields, post_load

from research_environment.identity_management.core import entities


class IdentityProvisioningRequest(Schema):
    user_name = fields.Str()
    password = fields.Str()
    recovery_email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()

    @post_load
    def make_cloud_identity(self, data, **kwargs):
        return entities.CloudIdentity.from_platform_data(**data)


class ProvisionedIdentity(Schema):
    email = fields.Str()
    recovery_email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()
