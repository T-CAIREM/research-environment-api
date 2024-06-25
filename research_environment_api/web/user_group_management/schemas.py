from marshmallow import Schema, fields


class UserGroupCreationRequest(Schema):
    group_name = fields.Str(required=True)
    description = fields.Str(required=True)


class UserGroupDeletionRequest(Schema):
    group_name = fields.Str(required=True)


class GoogleRole(Schema):
    full_name = fields.Str(required=True)
    title = fields.Str(required=True)
    description = fields.Str(required=True)


class GroupRoleListChangeRequest(Schema):
    group_name = fields.Str(required=True)
    role_list = fields.List(fields.Str(), required=True)


class GetGroupsRolesRequest(Schema):
    group_names = fields.List(fields.Str(), required=True)
