from enum import StrEnum

from google.cloud import asset, billing
from google.oauth2 import service_account


class IamBillingRole(StrEnum):
    ADMIN = "roles/billing.admin"
    USER = "roles/billing.user"


class BillingClient:
    def __init__(self, credentials: service_account.Credentials, organization_id: str):
        self.asset_service_client = asset.AssetServiceClient(credentials=credentials)
        self.cloud_billing_client = billing.CloudBillingClient(credentials=credentials)
        self.organization_scope = f"organizations/{organization_id}"

    def list_billing_account_iam_policies(self, email: str):
        query = (
            f"resource://cloudbilling.googleapis.com/billingAccounts policy: {email}"
        )

        return self.asset_service_client.search_all_iam_policies(
            scope=self.organization_scope, query=query
        )

    def list_active_billing_accounts(self):
        asset_types = ["cloudbilling.googleapis.com/BillingAccount"]
        query = "state: ACTIVE"

        return self.asset_service_client.search_all_resources(
            scope=self.organization_scope,
            asset_types=asset_types,
            query=query,
        )

    def create_membership_binding_for_billing_account(
        self,
        billing_account_id: str,
        member: str,
    ):
        resource = self._billing_account_resource_name(billing_account_id)
        policy = self._get_iam_policy_for_resource(resource)
        user_binding = self._get_policy_user_binding(policy)

        user_member = f"user:{member}"
        if user_binding is None:
            # No binding for "roles/billing.user" exists yet.
            user_binding = {"role": IamBillingRole.USER, "members": [user_member]}
            policy.bindings.append(user_binding)
        else:
            # A binding for "roles/billing.user" already exists.
            user_binding.members.append(user_member)

        return self.cloud_billing_client.set_iam_policy(
            policy=policy, resource=resource
        )

    def remove_membership_binding_for_billing_account(
        self,
        billing_account_id: str,
        member: str,
    ):
        resource = self._billing_account_resource_name(billing_account_id)
        policy = self._get_iam_policy_for_resource(resource)
        user_binding = self._get_policy_user_binding(policy)

        user_member = f"user:{member}"
        user_binding.members.remove(user_member)

        return self.cloud_billing_client.set_iam_policy(
            policy=policy, resource=resource
        )

    def _get_iam_policy_for_resource(self, resource: str):
        return self.cloud_billing_client.get_iam_policy(resource=resource)

    @staticmethod
    def _billing_account_resource_name(billing_account_id: str) -> str:
        return f"billingsAccounts/{billing_account_id}"

    @staticmethod
    def _get_policy_user_binding(policy):
        return next(
            filter(
                lambda binding: binding.role == IamBillingRole.USER, policy.bindings
            ),
            None,
        )
