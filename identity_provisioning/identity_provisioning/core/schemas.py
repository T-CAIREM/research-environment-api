from marshmallow import fields, post_load

from identity_provisioning.common import CamelCaseSchema
from identity_provisioning.core import entities


class GoogleWorkspaceUser(CamelCaseSchema):
    class Name(CamelCaseSchema):
        family_name = fields.Str()
        given_name = fields.Str()

    name = fields.Nested(Name())
    primary_email = fields.Str()
    password = fields.Str()
    change_password_at_next_login = fields.Bool()


class CloudIdentity(CamelCaseSchema):
    email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()

    @post_load
    def make_cloud_identity(self, data, **kwargs):
        return entities.CloudIdentity(**data)
