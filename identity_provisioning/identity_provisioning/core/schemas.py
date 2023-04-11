from marshmallow import Schema, fields, post_load

from identity_provisioning.core import entities


class CamelCaseSchema(Schema):
    def on_bind_field(self, field_name, field_obj):
        field_obj.data_key = self.camelize(field_obj.data_key or field_name)

    @staticmethod
    def camelize(s):
        parts = iter(s.split("_"))
        return next(parts) + "".join(i.title() for i in parts)


class GoogleWorkspaceUser(CamelCaseSchema):
    class Name(CamelCaseSchema):
        family_name = fields.Str()
        given_name = fields.Str()

    name = fields.Nested(Name())
    primary_email = fields.Str()
    password = fields.Str()
    change_password_at_next_login = fields.Bool()


class StoredCloudIdentityData(CamelCaseSchema):
    email = fields.Str()
    family_name = fields.Str()
    given_name = fields.Str()

    @post_load
    def make_stored_cloud_identity_data(self, data, **kwargs):
        return entities.StoredCloudIdentityData(**data)
