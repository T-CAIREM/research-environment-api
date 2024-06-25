from research_environment_api.modules.app import app
from research_environment_api.modules.user_group_management import entities

import itertools


def create_group(user_group_creation_entity: entities.UserGroupCreation):
    identity_client = app.config.cloud_identity_client
    group = {
        "labels": {"cloudidentity.googleapis.com/groups.discussion_forum": ""},
        "parent": f"organizations/{user_group_creation_entity.organization_id}",
        "displayName": f"hdn-{user_group_creation_entity.group_name}",
        "description": user_group_creation_entity.description,
        "groupKey": {
            "id": f"hdn-{user_group_creation_entity.group_name}@healthdatanexus.ai"
        },
    }
    group = identity_client.groups().create(group)
    return group


def _get_roles_associated_with_group(group_name: str, organization_id: str):
    organization_client = app.config.organization_client
    full_group_name = f"group:{group_name}@healthdatanexus.ai"

    response = organization_client.get_iam_policy(
        {"resource": f"organizations/{organization_id}"}
    )
    return [
        binding.role
        for binding in response.bindings
        if full_group_name in binding.members
    ]


def get_user_permissions(organization_id: str, user_groups: list[str]):
    user_permissions_list = [
        _get_roles_associated_with_group(group, organization_id)
        for group in user_groups
    ]
    flattened_user_permissions_list = list(
        itertools.chain.from_iterable(user_permissions_list)
    )
    return flattened_user_permissions_list
