from google.cloud.billing import CloudBillingClient

from google_auth import create_delegated_credentials_for


def list_billing_accounts(user_email: str):
    credentials = create_delegated_credentials_for(user_email)
    client = CloudBillingClient(credentials)
    return client.list_billing_accounts(user_email)
