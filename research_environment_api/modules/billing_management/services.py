import google.oauth2.service_account as service_account

import research_environment_api.library.google.iam as iam_api
import research_environment_api.modules.billing_management.enums as enums

BILLING_ACCOUNT_RESOURCE = "resource://cloudbilling.googleapis.com/billingAccounts"


def list_billing_accounts_for(
    credentials: service_account.Credentials, user_email: str, organization_id: str
):
    billing_iam_policies = iam_api.list_iam_policies(
        credentials,
        user_email,
        organization_id,
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


def share_billing_account_to(user_email: str, billing_account_resource_name: str):
    pass
