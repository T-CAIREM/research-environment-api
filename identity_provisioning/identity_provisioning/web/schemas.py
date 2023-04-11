from marshmallow import Schema, fields, post_load

from identity_provisioning.core import entities


class IdentityProvisioningRequest(Schema):
    family_name = fields.Str()
    given_name = fields.Str()
    user_name = fields.Str()
    password = fields.Str()

    @post_load
    def make_cloud_identity(self, data, **kwargs):
        return entities.CloudIdentity.from_platform_data(**data)


class ProvisionedIdentity(Schema):
    email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()
