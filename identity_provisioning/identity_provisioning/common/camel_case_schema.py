from marshmallow import Schema


class CamelCaseSchema(Schema):
    def on_bind_field(self, field_name, field_obj):
        field_obj.data_key = self.camelize(field_obj.data_key or field_name)

    @staticmethod
    def camelize(s):
        parts = iter(s.split("_"))
        return next(parts) + "".join(i.title() for i in parts)
