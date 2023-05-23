from enum import StrEnum

from google.cloud import asset, billing
from google.oauth2 import service_account


class IamBillingRole(StrEnum):
    ADMIN = "roles/billing.admin"
    USER = "roles/billing.user"


def list_billing_account_iam_policies(
    credentials: service_account.Credentials,
    organization_id: str,
    email: str,
):
    client = asset.AssetServiceClient(credentials=credentials)
    scope = f"organizations/{organization_id}"
    query = f"resource://cloudbilling.googleapis.com/billingAccounts policy: {email}"

    return client.search_all_iam_policies(request={"scope": scope, "query": query})


def get_iam_policy_for_billing_account(
    credentials: service_account.Credentials,
    billing_account_resource_name: str,
):
    client = billing.CloudBillingClient(credentials=credentials)
    return client.get_iam_policy(resource=billing_account_resource_name)


def create_membership_binding_for_billing_account(
    credentials: service_account.Credentials,
    billing_account_id: str,
    member: str,
):
    client = billing.CloudBillingClient(credentials=credentials)
    billing_account_resource_name = f"billingAccounts/{billing_account_id}"
    policy = get_iam_policy_for_billing_account(
        credentials, billing_account_resource_name
    )
    user_binding = next(
        filter(lambda binding: binding.role == IamBillingRole.USER, policy.bindings),
        None,
    )

    user_member = f"user:{member}"
    if user_binding is None:
        # No binding for "roles/billing.user" exists yet.
        user_binding = {"role": IamBillingRole.USER, "members": [user_member]}
        policy.bindings.append(user_binding)
    else:
        # A binding for "roles/billing.user" already exists.
        user_binding.members.append(user_member)

    request = {"policy": policy, "resource": billing_account_resource_name}
    return client.set_iam_policy(request=request)
