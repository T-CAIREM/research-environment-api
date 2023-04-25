from flask import current_app, request

from research_environment_api.web.billing_management import (
    billing_management_bp,
    schemas,
)
from research_environment_api.modules.billing_management import services


@billing_management_bp.get("/list")
def list_billing_accounts():
    body = request.get_json()
    list_billing_accounts_request = schemas.ListBillingAccountsRequest().load(body)

    user_email = list_billing_accounts_request["email"]
    credentials = current_app.config["SERVICE_ACCOUNT_CREDENTIALS"]

    billing_accounts = services.list_billing_accounts_for(user_email, credentials)
    serialized_billing_accounts = schemas.BillingAccount(many=True).dump(
        billing_accounts
    )

    return serialized_billing_accounts, 200
