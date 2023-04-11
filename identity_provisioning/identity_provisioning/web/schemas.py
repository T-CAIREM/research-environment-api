from marshmallow import Schema, fields, post_load

from identity_provisioning.core import entities


class GoogleWorkspaceUserCreation(Schema):
    class Name(Schema):
        family_name = fields.Str()
        given_name = fields.Str()

    name = fields.Nested(Name())
    primary_email = fields.Str()
    password = fields.Str()
    change_password_at_next_login = fields.Bool()

    @post_load
    def make_google_workspace_user(self, data, **kwargs):
        return entities.GooleWorkspaceUser.from_platform_data(**data)


class GoogleWorkspaceUser(Schema):
    class Name(Schema):
        family_name = fields.Str()
        given_name = fields.Str()

    name = fields.Nested(Name())
    primary_email = fields.Str()
    password = fields.Str()
    change_password_at_next_login = fields.Bool()


class CloudIdentity(Schema):
    email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()
