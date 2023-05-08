from google.cloud import asset, billing
from google.oauth2 import service_account


def list_iam_policies(
    credentials: service_account.Credentials,
    organization_id: str,
    email: str,
    resource: str,
):
    client = asset.AssetServiceClient(credentials=credentials)
    scope = f"organizations/{organization_id}"
    query = f"{resource} policy: {email}"

    return client.search_all_iam_policies(request={"scope": scope, "query": query})


def get_iam_policy_for_billing_account(
    credentials: service_account.Credentials,
    billing_account_resource_name: str,
):
    client = billing.CloudBillingClient(credentials=credentials)
    return client.get_iam_policy(resource=billing_account_resource_name)


def create_membership_binding_for_billing_account(
    credentials: service_account.Credentials,
    billing_account_resource_name: str,
):
    client = billing.CloudBillingClient(credentials=credentials)
    return client.set_iam_policy(resource=billing_account_resource_name)
