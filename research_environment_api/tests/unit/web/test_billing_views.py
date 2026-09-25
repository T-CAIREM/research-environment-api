import pytest
from google.api_core import exceptions as core_exceptions
from google.iam.v1 import policy_pb2

from research_environment_api.library.google import billing as billing_api
from research_environment_api.tests.helpers.fake_billing import (
    BILLING_ACCOUNT_ID,
    OWNER_EMAIL,
    SHARED_ROLE,
    USER_EMAIL,
    USER_MEMBER,
    FakeBillingIamClient,
    billing_client_backed_by,
    members,
)

ENDPOINTS = ["/billing/share", "/billing/revoke_access"]
REQUEST_BODY = {
    "owner_email": OWNER_EMAIL,
    "user_email": USER_EMAIL,
    "billing_account_id": BILLING_ACCOUNT_ID,
}


@pytest.fixture
def keep_swagger_file(mocker):
    # create_app() rewrites the committed web/static/swagger.json.
    mocker.patch("research_environment_api.web.app.persist_apispec")


@pytest.fixture
def app(keep_swagger_file, app):
    return app


@pytest.fixture
def api(client, mocker):
    # Imported only once the app exists: importing the web package earlier
    # pulls in the Celery worker, which initialises the real app config.
    from research_environment_api.web import decorators

    mocker.patch.object(
        decorators.id_token,
        "verify_oauth2_token",
        return_value={"aud": decorators.AUDIENCE},
    )
    return client


@pytest.fixture(autouse=True)
def clock(mocker):
    fake_time = mocker.patch.object(billing_api, "time")
    fake_time.monotonic.return_value = 0.0
    return fake_time


@pytest.fixture
def fake(mocker, mock_config):
    fake = FakeBillingIamClient(
        policy_pb2.Binding(role=SHARED_ROLE, members=[USER_MEMBER])
    )
    mock_config.google_billing_client = billing_client_backed_by(mocker, fake)
    return fake


def _post(client, endpoint):
    return client.post(
        endpoint, json=REQUEST_BODY, headers={"Authorization": "Bearer test-token"}
    )


def test_share_succeeds_after_a_conflict(api, fake):
    fake.set_errors.append(core_exceptions.Aborted("concurrent policy changes"))
    fake.policy.ClearField("bindings")

    response = _post(api, "/billing/share")

    assert response.status_code == 200
    assert members(fake.policy, SHARED_ROLE) == {USER_MEMBER}


def test_revoke_succeeds(api, fake):
    response = _post(api, "/billing/revoke_access")

    assert response.status_code == 200
    assert members(fake.policy, SHARED_ROLE) == set()


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize(
    "error",
    [
        core_exceptions.Aborted("There were concurrent policy changes."),
        core_exceptions.ServiceUnavailable("unavailable"),
    ],
    ids=["conflict", "transient"],
)
def test_exhausted_retries_return_503_with_retry_after(api, fake, endpoint, error):
    from research_environment_api.web.billing_management import error_handlers

    fake.get_errors.extend(error for _ in range(billing_api.POLICY_UPDATE_MAX_ATTEMPTS))

    response = _post(api, endpoint)

    assert response.status_code == 503
    assert response.headers["Retry-After"] == str(error_handlers.RETRY_AFTER_SECONDS)
    assert "retry" in response.get_json()["error"]
    assert USER_EMAIL not in response.get_data(as_text=True)
