import logging

import pytest
from google.api_core import exceptions as core_exceptions
from google.iam.v1 import policy_pb2

from research_environment_api.library.google import billing as billing_api
from research_environment_api.tests.helpers.fake_billing import (
    ADMIN_ROLE,
    BILLING_ACCOUNT_ID,
    OWNER_EMAIL,
    RESOURCE,
    SHARED_ROLE,
    USER_EMAIL,
    USER_MEMBER,
    FakeBillingIamClient,
    billing_client_backed_by,
    members,
)

OTHER_MEMBER = "user:bob@example.com"
OWNER_BINDING = policy_pb2.Binding(role=ADMIN_ROLE, members=[f"user:{OWNER_EMAIL}"])

TRANSIENT_ERRORS = [
    core_exceptions.InternalServerError,
    core_exceptions.BadGateway,
    core_exceptions.ServiceUnavailable,
    core_exceptions.GatewayTimeout,
    core_exceptions.DeadlineExceeded,
]


@pytest.fixture(autouse=True)
def clock(mocker):
    # Replaces the billing module's view of `time` only: no real sleeping, and
    # a clock that stays at 0 unless a test moves it.
    fake_time = mocker.patch.object(billing_api, "time")
    fake_time.monotonic.return_value = 0.0
    return fake_time


@pytest.fixture
def sleep(clock):
    return clock.sleep


def _share(mocker, fake):
    return billing_client_backed_by(
        mocker, fake
    ).create_membership_binding_for_billing_account(
        owner_email=OWNER_EMAIL,
        user_email=USER_EMAIL,
        billing_account_id=BILLING_ACCOUNT_ID,
    )


def _revoke(mocker, fake):
    return billing_client_backed_by(
        mocker, fake
    ).remove_membership_binding_for_billing_account(
        owner_email=OWNER_EMAIL,
        user_email=USER_EMAIL,
        billing_account_id=BILLING_ACCOUNT_ID,
    )


def _add(member):
    return lambda policy: billing_api._add_member(policy, SHARED_ROLE, member)


def _remove(member):
    return lambda policy: billing_api._remove_member(policy, SHARED_ROLE, member)


class TestShare:
    def test_creates_the_role_binding_when_it_does_not_exist(self, mocker, sleep):
        fake = FakeBillingIamClient(OWNER_BINDING)

        _share(mocker, fake)

        assert len(fake.get_calls) == 1
        assert len(fake.set_calls) == 1
        sent = fake.set_calls[0]["policy"]
        assert sent.etag == b"etag-1"
        assert members(sent, SHARED_ROLE) == {USER_MEMBER}
        assert members(sent, ADMIN_ROLE) == {f"user:{OWNER_EMAIL}"}
        sleep.assert_not_called()

    def test_appends_to_the_existing_role_binding(self, mocker):
        fake = FakeBillingIamClient(
            OWNER_BINDING, policy_pb2.Binding(role=SHARED_ROLE, members=[OTHER_MEMBER])
        )

        _share(mocker, fake)

        sent = fake.set_calls[0]["policy"]
        assert [binding.role for binding in sent.bindings] == [ADMIN_ROLE, SHARED_ROLE]
        assert members(sent, SHARED_ROLE) == {OTHER_MEMBER, USER_MEMBER}

    def test_member_already_present_skips_the_write(self, mocker):
        fake = FakeBillingIamClient(
            policy_pb2.Binding(role=SHARED_ROLE, members=[USER_MEMBER])
        )

        _share(mocker, fake)

        assert len(fake.get_calls) == 1
        assert fake.set_calls == []

    def test_disables_client_retry_and_caps_each_call(self, mocker):
        fake = FakeBillingIamClient()

        _share(mocker, fake)

        assert fake.get_calls == [
            {
                "resource": RESOURCE,
                "retry": None,
                "timeout": billing_api.POLICY_CALL_TIMEOUT_SECONDS,
            }
        ]
        assert fake.set_calls[0]["retry"] is None
        assert fake.set_calls[0]["timeout"] == billing_api.POLICY_CALL_TIMEOUT_SECONDS
        assert fake.set_calls[0]["request"]["resource"] == RESOURCE

    def test_concurrent_change_is_retried_from_a_fresh_read_and_kept(
        self, mocker, sleep
    ):
        # Another writer adds a member between our read and our write, so our
        # first write carries a stale etag and the fake rejects it with Aborted.
        fake = FakeBillingIamClient(OWNER_BINDING)
        fake.concurrent_changes.append(_add(OTHER_MEMBER))

        _share(mocker, fake)

        assert len(fake.get_calls) == 2
        assert [call["policy"].etag for call in fake.set_calls] == [
            b"etag-1",
            b"etag-2",
        ]
        # Neither the concurrent grant nor ours is lost.
        assert members(fake.policy, SHARED_ROLE) == {OTHER_MEMBER, USER_MEMBER}
        assert sleep.call_count == 1

    @pytest.mark.parametrize(
        "conflict", [core_exceptions.Aborted, core_exceptions.Conflict]
    )
    def test_conflict_on_first_write_rereads_and_uses_latest_etag(
        self, mocker, conflict
    ):
        fake = FakeBillingIamClient()
        fake.set_errors.append(conflict("There were concurrent policy changes."))
        fake.concurrent_changes.append(_add(OTHER_MEMBER))

        _share(mocker, fake)

        assert len(fake.get_calls) == 2
        final_set = fake.set_calls[-1]["policy"]
        assert final_set.etag == b"etag-2"
        assert members(final_set, SHARED_ROLE) == {OTHER_MEMBER, USER_MEMBER}

    def test_share_racing_a_revoke_does_not_restore_the_revoked_member(self, mocker):
        # Our share reads a policy that still has the other member; a revoke of
        # that member commits before our write.
        fake = FakeBillingIamClient(
            policy_pb2.Binding(role=SHARED_ROLE, members=[OTHER_MEMBER])
        )
        fake.concurrent_changes.append(_remove(OTHER_MEMBER))

        _share(mocker, fake)

        assert members(fake.policy, SHARED_ROLE) == {USER_MEMBER}

    @pytest.mark.parametrize("transient", TRANSIENT_ERRORS)
    def test_transient_error_on_read_is_retried(self, mocker, sleep, transient):
        fake = FakeBillingIamClient()
        fake.get_errors.append(transient("upstream hiccup"))

        _share(mocker, fake)

        assert len(fake.get_calls) == 2
        assert len(fake.set_calls) == 1
        assert members(fake.policy, SHARED_ROLE) == {USER_MEMBER}
        assert sleep.call_count == 1

    def test_service_unavailable_on_write_is_retried(self, mocker):
        fake = FakeBillingIamClient()
        fake.set_errors.append(core_exceptions.ServiceUnavailable("try again"))

        _share(mocker, fake)

        assert len(fake.get_calls) == 2
        assert len(fake.set_calls) == 2
        assert members(fake.policy, SHARED_ROLE) == {USER_MEMBER}

    def test_failed_precondition_is_not_retried(self, mocker, sleep):
        fake = FakeBillingIamClient()
        fake.set_errors.append(core_exceptions.FailedPrecondition("bad request"))

        with pytest.raises(core_exceptions.FailedPrecondition):
            _share(mocker, fake)

        assert len(fake.get_calls) == 1
        assert len(fake.set_calls) == 1
        sleep.assert_not_called()

    def test_persistent_conflict_raises_after_max_attempts(self, mocker, sleep):
        fake = FakeBillingIamClient()
        fake.set_errors.extend(
            core_exceptions.Aborted("There were concurrent policy changes.")
            for _ in range(billing_api.POLICY_UPDATE_MAX_ATTEMPTS)
        )

        with pytest.raises(billing_api.BillingPolicyConflictError) as raised:
            _share(mocker, fake)

        assert isinstance(raised.value.__cause__, core_exceptions.Aborted)
        assert len(fake.get_calls) == billing_api.POLICY_UPDATE_MAX_ATTEMPTS
        assert len(fake.set_calls) == billing_api.POLICY_UPDATE_MAX_ATTEMPTS
        assert sleep.call_count == billing_api.POLICY_UPDATE_MAX_ATTEMPTS - 1

    def test_persistent_transient_error_raises_update_error(self, mocker):
        fake = FakeBillingIamClient()
        fake.get_errors.extend(
            core_exceptions.ServiceUnavailable("down")
            for _ in range(billing_api.POLICY_UPDATE_MAX_ATTEMPTS)
        )

        with pytest.raises(billing_api.BillingPolicyUpdateError) as raised:
            _share(mocker, fake)

        assert not isinstance(raised.value, billing_api.BillingPolicyConflictError)
        assert fake.set_calls == []

    def test_stops_retrying_at_the_deadline(self, mocker, clock, sleep):
        # The clock reaches the deadline during the first attempt.
        clock.monotonic.side_effect = [
            0.0,
            billing_api.POLICY_UPDATE_DEADLINE_SECONDS,
        ]
        fake = FakeBillingIamClient()
        fake.set_errors.append(core_exceptions.Aborted("conflict"))

        with pytest.raises(billing_api.BillingPolicyConflictError):
            _share(mocker, fake)

        assert len(fake.get_calls) == 1
        sleep.assert_not_called()

    def test_retry_logs_carry_no_email(self, mocker, caplog):
        fake = FakeBillingIamClient()
        fake.set_errors.append(core_exceptions.Aborted(f"conflict on {USER_MEMBER}"))

        with caplog.at_level(logging.WARNING):
            _share(mocker, fake)

        retry_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(retry_logs) == 1
        assert "attempt 1/" in retry_logs[0].getMessage()
        assert "Aborted" in retry_logs[0].getMessage()
        assert "@" not in retry_logs[0].getMessage()


class TestRevoke:
    def test_removes_a_present_member_keeping_the_etag(self, mocker):
        fake = FakeBillingIamClient(
            OWNER_BINDING,
            policy_pb2.Binding(role=SHARED_ROLE, members=[USER_MEMBER, OTHER_MEMBER]),
        )

        _revoke(mocker, fake)

        assert len(fake.set_calls) == 1
        sent = fake.set_calls[0]["policy"]
        assert sent.etag == b"etag-1"
        assert members(sent, SHARED_ROLE) == {OTHER_MEMBER}
        assert members(sent, ADMIN_ROLE) == {f"user:{OWNER_EMAIL}"}

    def test_drops_the_binding_when_its_last_member_is_removed(self, mocker):
        fake = FakeBillingIamClient(
            OWNER_BINDING, policy_pb2.Binding(role=SHARED_ROLE, members=[USER_MEMBER])
        )

        _revoke(mocker, fake)

        sent = fake.set_calls[0]["policy"]
        assert [binding.role for binding in sent.bindings] == [ADMIN_ROLE]

    def test_absent_member_skips_the_write(self, mocker):
        fake = FakeBillingIamClient(
            OWNER_BINDING, policy_pb2.Binding(role=SHARED_ROLE, members=[OTHER_MEMBER])
        )

        _revoke(mocker, fake)

        assert len(fake.get_calls) == 1
        assert fake.set_calls == []

    def test_absent_role_binding_skips_the_write(self, mocker):
        fake = FakeBillingIamClient(OWNER_BINDING)

        _revoke(mocker, fake)

        assert fake.set_calls == []

    def test_revoke_racing_a_share_keeps_both_changes(self, mocker, sleep):
        fake = FakeBillingIamClient(
            policy_pb2.Binding(role=SHARED_ROLE, members=[USER_MEMBER])
        )
        fake.concurrent_changes.append(_add(OTHER_MEMBER))

        _revoke(mocker, fake)

        assert len(fake.get_calls) == 2
        assert fake.set_calls[-1]["policy"].etag == b"etag-2"
        assert members(fake.policy, SHARED_ROLE) == {OTHER_MEMBER}
        assert sleep.call_count == 1


class TestBackoff:
    def test_ceiling_doubles_up_to_the_cap(self, mocker):
        mocker.patch.object(billing_api.random, "uniform", side_effect=lambda a, b: b)

        delays = [billing_api._backoff_delay(attempt) for attempt in range(1, 7)]

        assert delays == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0]

    def test_full_jitter_can_sleep_as_little_as_zero(self, mocker):
        mocker.patch.object(billing_api.random, "uniform", side_effect=lambda a, b: a)

        assert billing_api._backoff_delay(4) == 0

    def test_worst_case_backoff_fits_the_deadline(self):
        worst_case = sum(
            min(
                billing_api.POLICY_UPDATE_BASE_BACKOFF_SECONDS * 2 ** (attempt - 1),
                billing_api.POLICY_UPDATE_MAX_BACKOFF_SECONDS,
            )
            for attempt in range(1, billing_api.POLICY_UPDATE_MAX_ATTEMPTS)
        )

        assert worst_case < billing_api.POLICY_UPDATE_DEADLINE_SECONDS
