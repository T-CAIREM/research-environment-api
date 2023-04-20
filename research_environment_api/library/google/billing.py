from google.oauth2 import service_account
from google.cloud.billing import CloudBillingClient

from research_environment_api.library.google.delegation import delegated


@delegated(scopes=["https://www.googleapis.com/auth/cloud-billing.readonly"])
def list_billing_accounts(delegated_credentials: service_account.Credentials):
    client = CloudBillingClient(credentials=delegated_credentials)
    return client.list_billing_accounts()
