from research_environment_api.modules.app import app
from research_environment_api.modules.user_group_management import entities

import itertools


def _get_full_group_name(group_name: str):
    return f"hdn-{group_name}@healthdatanexus.ai"


def create_group(user_group_creation_entity: entities.UserGroupCreation):
    identity_client = app.config.cloud_identity_client
    group = {
        "labels": {"cloudidentity.googleapis.com/groups.discussion_forum": ""},
        "parent": f"customers/{user_group_creation_entity.customer_id}",
        "displayName": f"hdn-{user_group_creation_entity.group_name}",
        "description": user_group_creation_entity.description,
        "groupKey": {"id": _get_full_group_name(user_group_creation_entity.group_name)},
    }
    group = (
        identity_client.groups()
        .create(body=group, initialGroupConfig="WITH_INITIAL_OWNER")
        .execute()
    )
    return group


def delete_group(user_group_deletion_entity: entities.UserGroupDeletion):
    identity_client = app.config.cloud_identity_client
    group_id = f"hdn-{user_group_deletion_entity.group_name}@healthdatanexus.ai"
    group = identity_client.groups().lookup(groupKey_id=group_id).execute()
    deleted_group = identity_client.groups().delete(name=group["name"]).execute()
    return deleted_group


def _get_roles_associated_with_group(group_name: str, organization_id: str):
    organization_client = app.config.organization_client
    full_group_name = _get_full_group_name(group_name)

    response = organization_client.get_iam_policy(
        {"resource": f"organizations/{organization_id}"}
    )
    return [
        binding.role
        for binding in response.bindings
        if full_group_name in binding.members
    ]


def get_roles_associated_with_service_account(
    service_account_name: str, project_id: str
):
    projects_client = app.config.google_cloud_resource_client
    full_group_name = f"serviceAccount:{service_account_name}@healthdatanexus.ai"
    response = projects_client.get_iam_policy({"resource": f"projects/{project_id}"})
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


def get_google_roles_list(
    user_group_role_listing_entity: entities.UserGroupRoleListing,
):
    iam_client = app.config.google_iam_client

    predefined_roles_pager = iam_client.list_roles()
    organization_roles_pager = iam_client.list_roles(
        request={
            "parent": f"organizations/{user_group_role_listing_entity.organization_id}"
        }
    )

    predefined_roles = [
        entities.GoogleRole.from_gcp_role(role_instance=role)
        for role in predefined_roles_pager
    ]
    organization_roles = [
        entities.GoogleRole.from_gcp_role(role_instance=role)
        for role in organization_roles_pager
    ]

    return predefined_roles + organization_roles


def add_role_to_group(add_role_to_group_entity: entities.ChangeGroupRoles):
    organization_client = app.config.organization_client
    full_group_name = _get_full_group_name(add_role_to_group_entity.group_name)
    group_binding = f"group:{full_group_name}"

    policy = organization_client.get_iam_policy(
        {"resource": f"organizations/{add_role_to_group_entity.organization_id}"}
    )
    google_bindings = policy.bindings
    for binding in google_bindings:
        if (
            binding.role in add_role_to_group_entity.role_list
            and group_binding not in binding["members"]
        ):
            binding["members"].add(group_binding)
            add_role_to_group_entity.role_list.remove(binding.role)

    for unassigned_role in add_role_to_group_entity.role_list:
        google_bindings.append(
            {"role": unassigned_role, "members": {f"{group_binding}"}}
        )

    organization_client.set_iam_policy(policy)


def remove_roles_from_group(remove_role_from_group_entity: entities.ChangeGroupRoles):
    organization_client = app.config.organization_client
    full_group_name = _get_full_group_name(remove_role_from_group_entity.group_name)
    group_binding = f"group:{full_group_name}"

    policy = organization_client.get_iam_policy(
        {"resource": f"organizations/{remove_role_from_group_entity.organization_id}"}
    )
    google_bindings = policy.bindings
    for binding in google_bindings:
        if (
            binding.role in remove_role_from_group_entity.role_list
            and group_binding not in binding["members"]
        ):
            binding["members"].remove(group_binding)
            remove_role_from_group_entity.role_list.remove(binding.role)

    organization_client.set_iam_policy(policy)
