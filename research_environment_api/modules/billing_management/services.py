import research_environment_api.library.google.billing as billing_api
from research_environment_api.modules import config
from research_environment_api.modules.billing_management import enums, exceptions


IAM_ROLE_MAPPING = {
    billing_api.IamBillingRole.ADMIN: enums.BillingAccountRole.OWNER,
    billing_api.IamBillingRole.USER: enums.BillingAccountRole.SHARED_USER,
}


def list_billing_accounts_for(user_email: str):
    credentials = config.app_config()["SERVICE_ACCOUNT_CREDENTIALS"]
    organization_id = config.app_config()["ORGANIZATION_ID"]

    billing_iam_policies = billing_api.list_billing_account_iam_policies(
        credentials,
        organization_id,
        user_email,
    )

    billing_accounts_by_role = {role: [] for role in enums.BillingAccountRole}

    for billing_iam_policy in billing_iam_policies:
        for role_binding in billing_iam_policy.policy.bindings:
            if role_binding.role not in IAM_ROLE_MAPPING:
                continue

            mapped_role = IAM_ROLE_MAPPING[role_binding.role]
            billing_accounts_by_role[mapped_role].append(billing_iam_policy.resource)

    return billing_accounts_by_role


def share_billing_account_to(
    owner_email: str,
    user_email: str,
    billing_account_resource_name: str,
):
    credentials = config.app_config()["SERVICE_ACCOUNT_CREDENTIALS"]
    organization_id = config.app_config()["ORGANIZATION_ID"]

    verify_billing_account_ownership(
        credentials, owner_email, organization_id, billing_account_resource_name
    )
    billing_api.create_membership_binding_for_billing_account(
        credentials, billing_account_resource_name, user_email
    )


def verify_billing_account_ownership(
    user_email: str,
    billing_account_resource_name: str,
):
    credentials = config.app_config()["SERVICE_ACCOUNT_CREDENTIALS"]
    organization_id = config.app_config()["ORGANIZATION_ID"]

    owned_billing_accounts = list_billing_accounts_for(
        credentials, user_email, organization_id
    )[billing_api.IamBillingRole.OWNER]

    if billing_account_resource_name not in owned_billing_accounts:
        raise exceptions.InsufficientPermissionError
