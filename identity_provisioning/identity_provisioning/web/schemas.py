from marshmallow import Schema, fields, post_load

from identity_provisioning.core import entities


class IdentityProvisioningRequest(Schema):
    class Name(Schema):
        family_name = fields.Str()
        given_name = fields.Str()

    name = fields.Nested(Name())
    primary_email = fields.Str()
    password = fields.Str()
    change_password_at_next_login = fields.Bool()

    @post_load
    def make_cloud_identity(self, data, **kwargs):
        return entities.CloudIdentity.from_platform_data(**data)


class GoogleWorkspaceUser(Schema):
    class Name(Schema):
        family_name = fields.Str()
        given_name = fields.Str()

    name = fields.Nested(Name())
    primary_email = fields.Str()
    password = fields.Str()
    change_password_at_next_login = fields.Bool()


class ProvisionedIdentity(Schema):
    email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()
