from marshmallow import Schema, fields, post_load

from identity_provisioning import core


class CloudIdentityCreation(CamelCaseSchema):
    user_name = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()

    @post_load
    def make_cloud_identity(self, data, **kwargs):
        return core.entities.CloudIdentity.from_platform_data(**data)
