from unittest.mock import MagicMock

from google.api_core import exceptions as core_exceptions
from google.iam.v1 import policy_pb2

from research_environment_api.library.google import billing as billing_api

OWNER_EMAIL = "owner@example.com"
USER_EMAIL = "alice@example.com"
USER_MEMBER = f"user:{USER_EMAIL}"
BILLING_ACCOUNT_ID = "000000-000000-000000"
RESOURCE = f"billingAccounts/{BILLING_ACCOUNT_ID}"
SHARED_ROLE = billing_api.IamBillingRole.USER
ADMIN_ROLE = billing_api.IamBillingRole.ADMIN


def copy_policy(policy: policy_pb2.Policy) -> policy_pb2.Policy:
    copy = policy_pb2.Policy()
    copy.CopyFrom(policy)
    return copy


def members(policy: policy_pb2.Policy, role: str) -> set:
    return {
        member
        for binding in policy.bindings
        if binding.role == role
        for member in binding.members
    }


class FakeBillingIamClient:
    """In-memory stand-in for CloudBillingClient's IAM methods.

    Like the real setIamPolicy, it rejects a write whose etag does not match
    the stored policy with `Aborted`, and moves to a new etag on every change.
    """

    def __init__(self, *bindings: policy_pb2.Binding):
        self.policy = policy_pb2.Policy(version=1, bindings=bindings)
        self._version = 0
        self._bump_etag()
        self.get_calls = []
        self.set_calls = []
        self.get_errors = []
        self.set_errors = []
        # Changes by another writer, each applied just before one of our sets.
        self.concurrent_changes = []

    def get_iam_policy(self, **kwargs):
        self.get_calls.append(kwargs)
        if self.get_errors:
            raise self.get_errors.pop(0)
        return copy_policy(self.policy)

    def set_iam_policy(self, **kwargs):
        sent = copy_policy(kwargs["request"]["policy"])
        self.set_calls.append({**kwargs, "policy": sent})
        if self.concurrent_changes:
            self.change_concurrently(self.concurrent_changes.pop(0))
        if self.set_errors:
            raise self.set_errors.pop(0)
        if sent.etag != self.policy.etag:
            raise core_exceptions.Aborted("There were concurrent policy changes.")
        self.policy = copy_policy(sent)
        self._bump_etag()
        return copy_policy(self.policy)

    def change_concurrently(self, change) -> None:
        change(self.policy)
        self._bump_etag()

    def _bump_etag(self) -> None:
        self._version += 1
        self.policy.etag = f"etag-{self._version}".encode()


def billing_client_backed_by(mocker, fake: FakeBillingIamClient):
    client = billing_api.BillingClient(credentials=MagicMock())
    mocker.patch.object(client, "_delegate_write_billing_client", return_value=fake)
    return client
