from typing import List, Dict

from research_environment_api.modules.billing_management import (
    internal,
    exceptions,
    enums,
)


# FIXME: Provide a concrete type for the mapping's values
def list_billing_accounts_for(
    user_email: str,
) -> List[Dict]:
    billing_accounts = internal.list_billing_accounts(user_email)
    return [
        {
            "id": billing_account.id,
            "name": billing_account.name,
            "cloud_link": internal.billing_account_cloud_link(billing_account.id),
            "is_owner": billing_account.role == enums.BillingAccountRole.OWNER,
        }
        for billing_account in billing_accounts
    ]


def share_billing_account_to(
    owner_email: str,
    user_email: str,
    billing_account_id: str,
):
    is_owner = internal.is_owner_of_billing_account(owner_email, billing_account_id)

    if not is_owner:
        raise exceptions.InsufficientPermissionError(
            "Owner email does not have the permission to manage the specified billing account"
        )

    return internal.give_user_billing_account_permission(
        owner_email=owner_email,
        user_email=user_email,
        billing_account_id=billing_account_id,
    )


def revoke_billing_account_access(
    owner_email: str,
    user_email: str,
    billing_account_id: str,
):
    is_owner = internal.is_owner_of_billing_account(owner_email, billing_account_id)

    if not is_owner:
        raise exceptions.InsufficientPermissionError(
            "Owner email does not have the permission to manage the specified billing account"
        )

    return internal.remove_user_billing_account_permission(
        user_email=user_email, billing_account_id=billing_account_id
    )
