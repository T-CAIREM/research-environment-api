import google.oauth2.service_account as service_account

import research_environment_api.library.google.billing as google_billing_api


def list_billing_accounts_for(
    user_email: str, credentials: service_account.Credentials
):
    return google_billing_api.list_billing_accounts(user_email, credentials)
