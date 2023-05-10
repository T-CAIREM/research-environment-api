from typing import Mapping, Any

import research_environment_api.library.google.billing as billing_api
from research_environment_api.modules import config
from research_environment_api.modules.billing_management import enums


IAM_ROLE_MAPPING = {
    billing_api.IamBillingRole.ADMIN: enums.BillingAccountRole.OWNER,
    billing_api.IamBillingRole.USER: enums.BillingAccountRole.SHARED_USER,
}


# FIXME: Provide a concrete type for the mapping's values
def list_billing_accounts_by_role(
    user_email: str,
) -> Mapping[enums.BillingAccountRole, Any]:
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
            formatted_resource_name = format_billing_account_resource_name(
                billing_iam_policy.resource
            )
            billing_accounts_by_role[mapped_role].append(formatted_resource_name)

    return billing_accounts_by_role


def give_user_billing_account_permission(
    user_email: str,
    billing_account_resource_name: str,
):
    credentials = config.app_config()["SERVICE_ACCOUNT_CREDENTIALS"]

    return billing_api.create_membership_binding_for_billing_account(
        credentials, billing_account_resource_name, user_email
    )


def is_owner_of_billing_account(
    user_email: str,
    billing_account_resource_name: str,
) -> bool:
    owner_role = enums.BillingAccountRole.OWNER
    owned_billing_accounts = list_billing_accounts_by_role(user_email)[owner_role]

    return billing_account_resource_name in owned_billing_accounts


def format_billing_account_resource_name(billing_account_resource_name: str) -> str:
    # Raw format: //cloudbilling.googleapis.com/billingAccounts/<billing_account_id>
    return billing_account_resource_name.removeprefix("//cloudbilling.googleapis.com/")
