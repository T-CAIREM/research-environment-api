import concurrent
from typing import Mapping, Any
from collections import namedtuple

import research_environment_api.library.google.billing as billing_api
from research_environment_api.modules import config
from research_environment_api.modules.billing_management import enums


IAM_ROLE_MAPPING = {
    billing_api.IamBillingRole.ADMIN: enums.BillingAccountRole.OWNER,
    billing_api.IamBillingRole.USER: enums.BillingAccountRole.SHARED_USER,
}

BillingAccount = namedtuple("BillingAccount", ["id", "name"])


def list_billing_accounts_by_role(
    user_email: str,
) -> Mapping[enums.BillingAccountRole, BillingAccount]:
    billing_account_resources = list_billing_account_resources_by_role(user_email)
    billing_accounts_by_role = {role: [] for role in enums.BillingAccountRole}

    for billing_account_resource in billing_account_resources:
        for role_binding in billing_account_resource["policy"].policy.bindings:
            if role_binding.role not in IAM_ROLE_MAPPING:
                continue

            billing_account_id = format_billing_account_resource_name(
                billing_account_resource["policy"].resource
            )
            billing_account_name = billing_account_resource["resource"].display_name

            billing_account = BillingAccount(
                id=billing_account_id, name=billing_account_name
            )
            mapped_role = IAM_ROLE_MAPPING[role_binding.role]
            billing_accounts_by_role[mapped_role].append(billing_account)

    return billing_accounts_by_role


def list_billing_account_resources_by_role(user_email: str) -> Mapping[Any, Any]:
    billing_client = config.app_config().google_billing_client

    with concurrent.futures.ThreadPoolExecutor() as executor:
        billing_iam_policies_future = executor.submit(
            billing_client.list_billing_account_iam_policies, user_email
        )
        billing_accounts_resources_future = executor.submit(
            billing_client.list_active_billing_accounts
        )

    billing_iam_policies = {
        policy.resource: policy for policy in billing_iam_policies_future.result()
    }
    billing_account_resources = billing_accounts_resources_future.result()

    return [
        {"resource": resource, "policy": billing_iam_policies[resource.name]}
        for resource in billing_account_resources.results
        if resource.name in billing_iam_policies
    ]


def give_user_billing_account_permission(
    user_email: str,
    billing_account_id: str,
):
    billing_client = config.app_config().google_billing_client

    return billing_client.create_membership_binding_for_billing_account(
        billing_account_id=billing_account_id, member=user_email
    )


def remove_user_billing_account_permission(
    user_email: str,
    billing_account_id: str,
):
    billing_client = config.app_config().google_billing_client

    return billing_client.remove_membership_binding_for_billing_account(
        billing_account_id=billing_account_id, member=user_email
    )


def is_owner_of_billing_account(
    user_email: str,
    billing_account_id: str,
) -> bool:
    owner_role = enums.BillingAccountRole.OWNER
    owned_billing_accounts = list_billing_accounts_by_role(user_email)[owner_role]
    owned_billing_account_ids = map(lambda account: account.id, owned_billing_accounts)

    return billing_account_id in owned_billing_account_ids


def billing_account_cloud_link(billing_account_id: str) -> str:
    return f"https://console.cloud.google.com/billing/{billing_account_id}"


def format_billing_account_resource_name(billing_account_resource_name: str) -> str:
    # Raw format: //cloudbilling.googleapis.com/billingAccounts/<billing_account_id>
    return billing_account_resource_name.removeprefix(
        "//cloudbilling.googleapis.com/billingAccounts/"
    )
