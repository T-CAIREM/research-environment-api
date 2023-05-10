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

    billing_accounts = services.list_billing_accounts_for(user_email)
    serialized_billing_accounts = schemas.BillingAccount(many=True).dump(
        billing_accounts
    )

    return serialized_billing_accounts, 200


@billing_management_bp.post("/share")
def share_billing_account():
    body = request.get_json()
    share_billing_account_request = schemas.ShareBillingAccountRequest().load(body)

    owner_email = share_billing_account_request["owner_email"]
    user_email = share_billing_account_request["user_email"]
    billing_account_resource_name = share_billing_account_request["resource_name"]

    services.share_billing_account_to(
        owner_email,
        user_email,
        billing_account_resource_name,
    )

    return "", 200
