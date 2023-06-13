from typing import Optional
from enum import StrEnum
from functools import cache

from google import protobuf
from google.cloud import billing
from google.oauth2 import service_account

from research_environment_api.library.google.delegation import (
    domain_delegate_credentials,
)


class IamBillingRole(StrEnum):
    ADMIN = "roles/billing.admin"
    USER = "organizations/3105849901/roles/hdn.shared_billing_account_user"


class BillingClient:
    def __init__(self, credentials: service_account.Credentials):
        self.credentials = credentials

    def list_active_billing_accounts(self, user_email):
        billing_accounts = self._delegate_readonly_billing_client(
            user_email=user_email
        ).list_billing_accounts()

        return [
            billing_account
            for billing_account in billing_accounts
            if billing_account.open_
        ]

    def get_iam_policy_for_billing_account(
        self, user_email: str, billing_account_id: str
    ):
        return self._delegate_readonly_billing_client(
            user_email=user_email
        ).get_iam_policy(resource=billing_account_id)

    def create_membership_binding_for_billing_account(
        self, owner_email: str, user_email: str, billing_account_id: str
    ):
        delegated_billing_client = self._delegate_write_billing_client(
            user_email=owner_email
        )

        resource = self._billing_account_resource_name(billing_account_id)
        policy = delegated_billing_client.get_iam_policy(resource=resource)
        new_policy = self._build_policy_with_user_member(policy, user_email)

        request = {"policy": new_policy, "resource": resource}
        return delegated_billing_client.set_iam_policy(request=request)

    def remove_membership_binding_for_billing_account(
        self,
        owner_email: str,
        user_email: str,
        billing_account_id: str,
    ):
        delegated_billing_client = self._delegate_write_billing_client(
            user_email=owner_email
        )

        resource = self._billing_account_resource_name(billing_account_id)
        policy = delegated_billing_client.get_iam_policy(resource=resource)
        new_policy = self._copy_policy(policy)
        user_binding = self._get_policy_user_binding(new_policy)
        if not user_binding:
            return

        user_member = f"user:{user_email}"
        if user_member not in user_binding["members"]:
            return
        user_binding["members"].remove(user_member)

        request = {"policy": new_policy, "resource": resource}
        return delegated_billing_client.set_iam_policy(request=request)

    def _build_policy_with_user_member(self, policy: dict, user_email: str) -> dict:
        new_policy = self._copy_policy(policy)
        user_binding = self._get_policy_user_binding(new_policy)
        user_member = f"user:{user_email}"

        if user_binding is None:
            user_binding = {"role": IamBillingRole.USER, "members": [user_member]}
            new_policy["bindings"].append(user_binding)
        else:
            user_binding["members"].append(user_member)

        return new_policy

    def _get_policy_user_binding(self, policy: dict) -> Optional[dict]:
        return next(
            filter(
                lambda binding: binding["role"] == IamBillingRole.USER,
                policy["bindings"],
            ),
            None,
        )

    def _copy_policy(self, policy) -> dict:
        policy_keys = ["members", "bindings"]
        # Filter out gRPC keys (version, etag)
        return {
            key: value
            for key, value in protobuf.json_format.MessageToDict(policy).items()
            if key in policy_keys
        }

    def _billing_account_resource_name(self, billing_account_id: str) -> str:
        return f"billingAccounts/{billing_account_id}"

    def _delegate_write_billing_client(
        self, user_email: str
    ) -> billing.CloudBillingClient:
        return self._delegate_billing_client(
            user_email, "https://www.googleapis.com/auth/cloud-billing"
        )

    def _delegate_readonly_billing_client(
        self, user_email: str
    ) -> billing.CloudBillingClient:
        return self._delegate_billing_client(
            user_email, "https://www.googleapis.com/auth/cloud-billing.readonly"
        )

    @cache
    def _delegate_billing_client(
        self, user_email: str, scope: str
    ) -> billing.CloudBillingClient:
        delegated_credentials = domain_delegate_credentials(
            self.credentials, user_email, [scope]
        )
        return billing.CloudBillingClient(credentials=delegated_credentials)
