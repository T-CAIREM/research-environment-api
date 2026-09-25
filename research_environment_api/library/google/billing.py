import random
import time
from enum import StrEnum
from functools import cache
from typing import Callable

from google.api_core import exceptions as core_exceptions
from google.cloud import billing
from google.iam.v1 import policy_pb2
from google.oauth2 import service_account

from research_environment_api.library.google.delegation import (
    domain_delegate_credentials,
)
from research_environment_api.modules.logger import logger

# Retry budget for the IAM policy read-modify-write behind /billing/share and
# /billing/revoke_access. Both endpoints are synchronous, so the budget has to
# fit inside a single HTTP request. Backoff sleeps total at most
# 1 + 2 + 4 + 8 + 8 = 23 s over 6 attempts (about half that on average, with
# full jitter). No attempt starts after the 25 s deadline, and each Google call
# is capped at 5 s, so a request gives up after about 35 s at worst. A burst of
# concurrent shares on one account normally settles within the first few
# attempts.
POLICY_UPDATE_MAX_ATTEMPTS = 6
POLICY_UPDATE_BASE_BACKOFF_SECONDS = 1.0
POLICY_UPDATE_MAX_BACKOFF_SECONDS = 8.0
POLICY_UPDATE_DEADLINE_SECONDS = 25.0
POLICY_CALL_TIMEOUT_SECONDS = 5.0

# Errors after which the whole read -> modify -> write cycle is retried.
# `Conflict` covers `Aborted` (gRPC ABORTED, "There were concurrent policy
# changes"), which setIamPolicy raises when the etag we send is stale, and a
# plain 409 on REST. `FailedPrecondition` maps to HTTP 400 and is deliberately
# not retried.
_RETRYABLE_POLICY_ERRORS = (
    core_exceptions.Conflict,
    core_exceptions.InternalServerError,
    core_exceptions.BadGateway,
    core_exceptions.ServiceUnavailable,
    core_exceptions.GatewayTimeout,
    core_exceptions.DeadlineExceeded,
)


class BillingPolicyUpdateError(Exception):
    """A billing account IAM policy update still failed after every retry.

    Raised only for conflicts and transient upstream errors, so the same
    request is safe to retry later.
    """


class BillingPolicyConflictError(BillingPolicyUpdateError):
    """Concurrent changes kept invalidating the policy etag on every attempt."""


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
    ) -> policy_pb2.Policy:
        user_member = f"user:{user_email}"
        return self._update_billing_account_policy(
            owner_email,
            billing_account_id,
            lambda policy: _add_member(policy, IamBillingRole.USER, user_member),
        )

    def remove_membership_binding_for_billing_account(
        self,
        owner_email: str,
        user_email: str,
        billing_account_id: str,
    ) -> policy_pb2.Policy:
        user_member = f"user:{user_email}"
        return self._update_billing_account_policy(
            owner_email,
            billing_account_id,
            lambda policy: _remove_member(policy, IamBillingRole.USER, user_member),
        )

    def _update_billing_account_policy(
        self,
        owner_email: str,
        billing_account_id: str,
        change_policy: Callable[[policy_pb2.Policy], bool],
    ) -> policy_pb2.Policy:
        """Read-modify-write the billing account's IAM policy, safely.

        `change_policy` edits the policy in place and returns whether it changed
        anything. Editing the Policy message we read keeps its etag and version,
        so setIamPolicy rejects the write with `Aborted` if anyone changed the
        policy since our read, instead of silently overwriting their change.
        On a conflict or a transient error the whole cycle runs again from a
        fresh read; a stale policy is never re-sent. This loop is the only retry
        layer: the client's built-in retry is disabled so that the
        POLICY_UPDATE_* budget holds.
        """
        delegated_billing_client = self._delegate_write_billing_client(
            user_email=owner_email
        )
        resource = self._billing_account_resource_name(billing_account_id)
        deadline = time.monotonic() + POLICY_UPDATE_DEADLINE_SECONDS

        for attempt in range(1, POLICY_UPDATE_MAX_ATTEMPTS + 1):
            try:
                policy = delegated_billing_client.get_iam_policy(
                    resource=resource,
                    retry=None,
                    timeout=POLICY_CALL_TIMEOUT_SECONDS,
                )
                if not change_policy(policy):
                    return policy
                return delegated_billing_client.set_iam_policy(
                    request={"resource": resource, "policy": policy},
                    retry=None,
                    timeout=POLICY_CALL_TIMEOUT_SECONDS,
                )
            except _RETRYABLE_POLICY_ERRORS as error:
                last_error = error

            delay = _backoff_delay(attempt)
            if (
                attempt == POLICY_UPDATE_MAX_ATTEMPTS
                or time.monotonic() + delay >= deadline
            ):
                break
            logger.warning(
                "Billing account IAM policy update attempt %d/%d failed with %s; "
                "retrying",
                attempt,
                POLICY_UPDATE_MAX_ATTEMPTS,
                type(last_error).__name__,
            )
            time.sleep(delay)

        logger.error(
            "Billing account IAM policy update gave up after %d attempt(s); "
            "last error %s",
            attempt,
            type(last_error).__name__,
        )
        if isinstance(last_error, core_exceptions.Conflict):
            raise BillingPolicyConflictError() from last_error
        raise BillingPolicyUpdateError() from last_error

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


def _backoff_delay(attempt: int) -> float:
    """Truncated exponential backoff with full jitter.

    The ceiling doubles per attempt (1, 2, 4, 8, 8 s) as in Google's retry
    guidance; sleeping a uniformly random fraction of it spreads out callers
    that collided on the same policy so they stop colliding again.
    """
    ceiling = min(
        POLICY_UPDATE_BASE_BACKOFF_SECONDS * 2 ** (attempt - 1),
        POLICY_UPDATE_MAX_BACKOFF_SECONDS,
    )
    return random.uniform(0, ceiling)


def _role_bindings(policy: policy_pb2.Policy, role: str) -> list:
    return [binding for binding in policy.bindings if binding.role == role]


def _add_member(policy: policy_pb2.Policy, role: str, member: str) -> bool:
    """Add `member` to `role` in place. Returns False if it is already there."""
    bindings = _role_bindings(policy, role)
    if any(member in binding.members for binding in bindings):
        return False
    if bindings:
        bindings[0].members.append(member)
    else:
        policy.bindings.add(role=role, members=[member])
    return True


def _remove_member(policy: policy_pb2.Policy, role: str, member: str) -> bool:
    """Remove `member` from `role` in place. Returns False if it is absent."""
    changed = False
    for binding in _role_bindings(policy, role):
        if member in binding.members:
            binding.members.remove(member)
            changed = True
            if not binding.members:
                policy.bindings.remove(binding)
    return changed
