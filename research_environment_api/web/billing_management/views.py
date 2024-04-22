from flask import request

from research_environment_api.modules.billing_management import services
from research_environment_api.web.billing_management import (
    billing_management_bp,
    schemas,
)
from research_environment_api.web.cache import cache
from research_environment_api.web.decorators import validate_token


@billing_management_bp.get("/<email>")
@validate_token
@cache.cached(timeout=300)
def list_billing_accounts(email: str):
    """Lists a user's billing accounts.
    ---
    get:
      tags:
        - billing_management
      description: Lists a user's billing accounts.
      parameters:
      - in: path
        name: email
        schema:
          type: string
      responses:
        200:
          description: Returns a list of billing accounts.
          content:
            application/json:
              schema:
                type: array
                items: BillingAccount
    """
    list_billing_accounts_request = schemas.ListBillingAccountsRequest().load(
        {"email": email}
    )
    user_email = list_billing_accounts_request["email"]

    billing_accounts = services.list_billing_accounts_for(user_email)
    serialized_billing_accounts = schemas.BillingAccount(many=True).dump(
        billing_accounts
    )

    return serialized_billing_accounts, 200


@billing_management_bp.post("/share")
@validate_token
def share_billing_account():
    """Shares a billing account.
    ---
    post:
      tags:
        - billing_management
      description: Shares a billing account.
      requestBody:
        content:
          application/json:
            schema: ShareBillingAccountRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    share_billing_account_request = schemas.ShareBillingAccountRequest().load(body)

    owner_email = share_billing_account_request["owner_email"]
    user_email = share_billing_account_request["user_email"]
    billing_account_id = share_billing_account_request["billing_account_id"]

    services.share_billing_account_to(
        owner_email,
        user_email,
        billing_account_id,
    )

    return {}, 200


@billing_management_bp.post("/revoke_access")
@validate_token
def revoke_billing_account_access():
    """Revokes a user's access to a billing account.
    ---
    post:
      tags:
        - billing_management
      description: Revokes a user's access to a billing account.
      requestBody:
        content:
          application/json:
            schema: RevokeBillingAccountAccessRequest
      responses:
        200:
          description: Returns an empty object.
          content:
            application/json:
              schema:
    """
    body = request.get_json()
    revoke_billing_account_access_request = (
        schemas.RevokeBillingAccountAccessRequest().load(body)
    )

    owner_email = revoke_billing_account_access_request["owner_email"]
    user_email = revoke_billing_account_access_request["user_email"]
    billing_account_id = revoke_billing_account_access_request["billing_account_id"]

    services.revoke_billing_account_access(
        owner_email,
        user_email,
        billing_account_id,
    )

    return {}, 200
