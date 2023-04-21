from google.oauth2 import service_account
from google.cloud.billing import CloudBillingClient, BillingAccount

from research_environment_api.library.google.delegation import with_delegated_client


@with_delegated_client(
    CloudBillingClient,
    scopes=["https://www.googleapis.com/auth/cloud-billing.readonly"],
)
def list_billing_accounts(client: CloudBillingClient):
    return client.list_billing_accounts()
