from research_environment_api.modules.billing_management import (
    internal,
    exceptions,
    enums,
)


# FIXME: Provide a concrete type for the mapping's values
def list_billing_accounts_for(
    user_email: str,
) -> list:
    billing_accounts_by_role = internal.list_billing_accounts_by_role(user_email)
    return [
        {
            "id": billing_account_id,
            "cloud_link": internal.billing_account_cloud_link(billing_account_id),
            "is_owner": role == enums.BillingAccountRole.OWNER,
        }
        for role, billing_account_ids in billing_accounts_by_role.items()
        for billing_account_id in billing_account_ids
    ]


def share_billing_account_to(
    owner_email: str,
    user_email: str,
    billing_account_resource_name: str,
):
    is_owner = internal.is_owner_of_billing_account(
        owner_email, billing_account_resource_name
    )

    if not is_owner:
        raise exceptions.InsufficientPermissionError("Insufficient permission")

    return internal.give_user_billing_account_permission(
        user_email, billing_account_resource_name
    )
