import google.oauth2.service_account as service_account

import research_environment_api.library.google.iam as iam_api
from research_environment_api.modules.billing_management import enums, exceptions

BILLING_ACCOUNT_RESOURCE = "resource://cloudbilling.googleapis.com/billingAccounts"


def list_billing_accounts_for(
    credentials: service_account.Credentials, organization_id: str, user_email: str
):
    billing_iam_policies = iam_api.list_iam_policies(
        credentials,
        organization_id,
        user_email,
        BILLING_ACCOUNT_RESOURCE,
    )

    supported_roles = [e for e in enums.IamBillingRole]
    billing_accounts_by_role = {role: [] for role in supported_roles}

    for billing_iam_policy in billing_iam_policies:
        for role_binding in billing_iam_policy.policy.bindings:
            if role_binding.role not in supported_roles:
                continue

            billing_accounts_by_role[role_binding.role].append(
                billing_iam_policy.resource
            )

    return billing_accounts_by_role


def share_billing_account_to(
    credentials: service_account.Credentials,
    organization_id: str,
    owner_email: str,
    user_email: str,
    billing_account_resource_name: str,
):
    verify_billing_account_ownership(
        credentials, owner_email, organization_id, billing_account_resource_name
    )


def verify_billing_account_ownership(
    credentials: service_account.Credentials,
    organization_id: str,
    user_email: str,
    billing_account_resource_name: str,
):
    owned_billing_accounts = list_billing_accounts_for(
        credentials, user_email, organization_id
    )[enums.IamBillingRole.OWNER]

    if billing_account_resource_name not in owned_billing_accounts:
        raise exceptions.InsufficientPermissionError
