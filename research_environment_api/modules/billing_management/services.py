from typing import Mapping

from research_environment_api.modules import config
from research_environment_api.modules.billing_management import (
    internal,
    exceptions,
    enums,
)


def list_billing_accounts_for(user_email: str) -> Mapping[enums.BillingAccountRole]:
    return internal.list_billing_accounts_by_role(user_email)


def share_billing_account_to(
    owner_email: str,
    user_email: str,
    billing_account_resource_name: str,
):
    is_owner = internal.verify_billing_account_ownership(
        owner_email, billing_account_resource_name
    )

    if not is_owner:
        raise exceptions.InsufficientPermissionError

    return internal.give_user_billing_account_permission(
        user_email, billing_account_resource_name
    )
