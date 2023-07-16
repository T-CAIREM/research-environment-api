from collections import namedtuple
from typing import List, Mapping, Optional

import research_environment_api.library.google.billing as billing_api
from research_environment_api.modules.app import app
from research_environment_api.modules.billing_management import entities, enums

IAM_ROLE_MAPPING = {
    billing_api.IamBillingRole.ADMIN: enums.BillingAccountRole.OWNER,
    billing_api.IamBillingRole.USER: enums.BillingAccountRole.SHARED_USER,
}


GoogleCloudBillingAccount = namedtuple(
    "GoogleCloudBillingAccount", ["id", "name", "role"]
)


# FIXME: Provide a concrete type for the mapping's values
def list_billing_accounts_for(
    user_email: str,
) -> List[entities.BillingAccount]:
    billing_accounts = _list_billing_accounts(user_email)
    return [
        entities.BillingAccount(
            id=billing_account.id,
            name=billing_account.name,
            cloud_link=_billing_account_cloud_link(billing_account.id),
            is_owner=(billing_account.role == enums.BillingAccountRole.OWNER),
        )
        for billing_account in billing_accounts
    ]


def share_billing_account_to(
    owner_email: str,
    user_email: str,
    billing_account_id: str,
):
    return _give_user_billing_account_permission(
        owner_email=owner_email,
        user_email=user_email,
        billing_account_id=billing_account_id,
    )


def revoke_billing_account_access(
    owner_email: str,
    user_email: str,
    billing_account_id: str,
):
    return _remove_user_billing_account_permission(
        owner_email=owner_email,
        user_email=user_email,
        billing_account_id=billing_account_id,
    )


def _list_billing_accounts(
    user_email: str,
) -> Mapping[enums.BillingAccountRole, GoogleCloudBillingAccount]:
    billing_client = app.config.google_billing_client
    billing_account_list = billing_client.list_active_billing_accounts(
        user_email=user_email
    )

    return [
        GoogleCloudBillingAccount(
            id=_format_billing_account_resource_name(account.name),
            name=account.display_name,
            role=role,
        )
        for account in billing_account_list
        if (role := _billing_account_role_for(user_email, account.name))
    ]


def _billing_account_role_for(
    user_email: str, billing_account_id: str
) -> Optional[enums.BillingAccountRole]:
    billing_client = app.config.google_billing_client
    iam_policy = billing_client.get_iam_policy_for_billing_account(
        user_email=user_email, billing_account_id=billing_account_id
    )
    binding_member = f"user:{user_email}"
    role_policy = next(
        filter(lambda binding: binding_member in binding.members, iam_policy.bindings),
        None,  # Role won't be found for billing accounts accessible via inherited permission (project/organisation level)
    )

    return role_policy and IAM_ROLE_MAPPING.get(role_policy.role, None)


def _give_user_billing_account_permission(
    owner_email: str,
    user_email: str,
    billing_account_id: str,
):
    billing_client = app.config.google_billing_client

    return billing_client.create_membership_binding_for_billing_account(
        owner_email=owner_email,
        user_email=user_email,
        billing_account_id=billing_account_id,
    )


def _remove_user_billing_account_permission(
    owner_email: str,
    user_email: str,
    billing_account_id: str,
):
    billing_client = app.config.google_billing_client

    return billing_client.remove_membership_binding_for_billing_account(
        owner_email=owner_email,
        user_email=user_email,
        billing_account_id=billing_account_id,
    )


def _billing_account_cloud_link(billing_account_id: str) -> str:
    return f"https://console.cloud.google.com/billing/{billing_account_id}"


def _format_billing_account_resource_name(billing_account_resource_name: str) -> str:
    # Raw format: billingAccounts/<billing_account_id>
    return billing_account_resource_name.removeprefix("billingAccounts/")
