from enum import StrEnum

from google.cloud import asset, billing
from google.oauth2 import service_account


class IamBillingRole(StrEnum):
    ADMIN = "roles/billing.admin"
    USER = "roles/billing.user"


class BillingClient:
    def __init__(self, credentials: service_account.Credentials):
        self.asset_service_client = asset.AssetServiceClient(credentials=credentials)
        self.cloud_billing_client = billing.CloudBillingClient(credentials=credentials)

    def list_billing_account_iam_policies(
        self,
        organization_id: str,
        email: str,
    ):
        scope = f"organizations/{organization_id}"
        query = (
            f"resource://cloudbilling.googleapis.com/billingAccounts policy: {email}"
        )

        return self.asset_service_client.search_all_iam_policies(
            request={"scope": scope, "query": query}
        )

    def get_iam_policy_for_billing_account(
        self,
        billing_account_resource_name: str,
    ):
        return self.cloud_billing_client.get_iam_policy(
            resource=billing_account_resource_name
        )

    def create_membership_binding_for_billing_account(
        self,
        billing_account_id: str,
        member: str,
    ):
        billing_account_resource_name = f"billingAccounts/{billing_account_id}"
        policy = self.get_iam_policy_for_billing_account(billing_account_resource_name)
        user_binding = self._get_policy_user_binding(policy)

        user_member = f"user:{member}"
        if user_binding is None:
            # No binding for "roles/billing.user" exists yet.
            user_binding = {"role": IamBillingRole.USER, "members": [user_member]}
            policy.bindings.append(user_binding)
        else:
            # A binding for "roles/billing.user" already exists.
            user_binding.members.append(user_member)

        request = {"policy": policy, "resource": billing_account_resource_name}
        return self.cloud_billing_client.set_iam_policy(request=request)

    def remove_membership_binding_for_billing_account(
        self,
        billing_account_id: str,
        member: str,
    ):
        billing_account_resource_name = f"billingAccounts/{billing_account_id}"
        policy = self.get_iam_policy_for_billing_account(billing_account_resource_name)
        user_binding = self._get_policy_user_binding(policy)

        user_member = f"user:{member}"
        user_binding.members.remove(user_member)

        request = {"policy": policy, "resource": billing_account_resource_name}
        return self.cloud_billing_client.set_iam_policy(request=request)

    @staticmethod
    def _get_policy_user_binding(policy):
        return next(
            filter(
                lambda binding: binding.role == IamBillingRole.USER, policy.bindings
            ),
            None,
        )
