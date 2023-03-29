from marshmallow import Schema, fields, post_load

from identity_provisioning.common import CamelCaseSchema
from identity_provisioning.core import entities


class CloudIdentityCreation(CamelCaseSchema):
    user_name = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()

    @post_load
    def make_cloud_identity(self, data, **kwargs):
        return entities.CloudIdentity.from_platform_data(**data)
