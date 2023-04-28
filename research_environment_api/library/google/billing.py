from functools import partial

from google.oauth2 import service_account

from research_environment_api.library.google import iam


def list_billing_accounts_by_role(
    role: str,
    credentials: service_account.Credentials,
    email: str,
    organization_id: str,
):
    results = iam.list_organization_policies(
        email,
        credentials,
        organization_id,
        "resource://cloudbilling.googleapis.com/billingAccounts",
    )

    billing_accounts_with_role = [
        policy_result.resource
        for policy_result in results
        if any(binding.role == role for binding in policy_result.policy.bindings)
    ]
    return billing_accounts_with_role


list_owned_billing_accounts = partial(
    list_billing_accounts_by_role, "roles/billing.admin"
)


list_shared_billing_accounts = partial(
    list_billing_accounts_by_role, "roles/billing.user"
)
