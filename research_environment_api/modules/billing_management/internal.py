from typing import Mapping, Optional
from collections import namedtuple

import research_environment_api.library.google.billing as billing_api
from research_environment_api.modules.config import config
from research_environment_api.modules.billing_management import enums


IAM_ROLE_MAPPING = {
    billing_api.IamBillingRole.ADMIN: enums.BillingAccountRole.OWNER,
    billing_api.IamBillingRole.USER: enums.BillingAccountRole.SHARED_USER,
}

BillingAccount = namedtuple("BillingAccount", ["id", "name", "role"])


def list_billing_accounts(
    user_email: str,
) -> Mapping[enums.BillingAccountRole, BillingAccount]:
    billing_client = config.google_billing_client
    billing_account_list = billing_client.list_active_billing_accounts(
        user_email=user_email
    )

    return [
        BillingAccount(
            id=format_billing_account_resource_name(account.name),
            name=account.display_name,
            role=role,
        )
        for account in billing_account_list
        if (role := billing_account_role_for(user_email, account.name))
    ]


def billing_account_role_for(
    user_email: str, billing_account_id: str
) -> Optional[enums.BillingAccountRole]:
    billing_client = config.google_billing_client
    iam_policy = billing_client.get_iam_policy_for_billing_account(
        user_email=user_email, billing_account_id=billing_account_id
    )
    binding_member = f"user:{user_email}"
    role_policy = next(
        filter(lambda binding: binding_member in binding.members, iam_policy.bindings),
        None,  # Role won't be found for billing accounts accessible via inherited permission (project/organisation level)
    )

    return role_policy and IAM_ROLE_MAPPING.get(role_policy.role, None)


def give_user_billing_account_permission(
    owner_email: str,
    user_email: str,
    billing_account_id: str,
):
    billing_client = config.google_billing_client

    return billing_client.create_membership_binding_for_billing_account(
        owner_email=owner_email,
        user_email=user_email,
        billing_account_id=billing_account_id,
    )


def remove_user_billing_account_permission(
    owner_email: str,
    user_email: str,
    billing_account_id: str,
):
    billing_client = config.google_billing_client

    return billing_client.remove_membership_binding_for_billing_account(
        owner_email=owner_email,
        user_email=user_email,
        billing_account_id=billing_account_id,
    )


def billing_account_cloud_link(billing_account_id: str) -> str:
    return f"https://console.cloud.google.com/billing/{billing_account_id}"


def format_billing_account_resource_name(billing_account_resource_name: str) -> str:
    # Raw format: billingAccounts/<billing_account_id>
    return billing_account_resource_name.removeprefix("billingAccounts/")
