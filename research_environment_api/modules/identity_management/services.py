from research_environment_api.library.google import workspace as google_workspace
from research_environment_api.modules.logger import logger
from research_environment_api.modules.config import config
from research_environment_api.modules.identity_management import (
    entities,
    exceptions,
)


def provision_cloud_identity(
    cloud_identity_creation: entities.CloudIdentityCreation,
) -> entities.CloudIdentityCreation:
    _create_google_workspace_user(cloud_identity_creation)
    _allow_to_create_billing_accounts(cloud_identity_creation)

    return cloud_identity_creation


def _create_google_workspace_user(
    cloud_identity_creation: entities.CloudIdentityCreation,
):
    try:
        _create_cloud_identity_in_google_workspace(cloud_identity_creation)
    except exceptions.GoogleWorkspaceUserAlreadyExistsError:
        logger.warning(
            f"{cloud_identity_creation.primary_email} already created in Google Workspace"
        )


def _allow_to_create_billing_accounts(
    cloud_identity_creation: entities.CloudIdentityCreation,
):
    try:
        _allow_to_create_billing_accounts(cloud_identity_creation)
    except exceptions.BillingCreatorGroupMembershipAlreadyExistsError:
        logger.warning(
            f"{cloud_identity_creation.primary_email} already a member of the billing account creator group"
        )


def _create_cloud_identity_in_google_workspace(
    cloud_identity_creation: entities.CloudIdentityCreation,
):
    google_workspace_client = _build_google_workspace_client()

    google_workspace_user = {
        "name": {
            "givenName": cloud_identity_creation.given_name,
            "familyName": cloud_identity_creation.family_name,
        },
        "primaryEmail": cloud_identity_creation.primary_email,
        "recoveryEmail": cloud_identity_creation.recovery_email,
        "password": cloud_identity_creation.password,
    }

    try:
        google_workspace_client.create_user(google_workspace_user)
    except google_workspace.UserAlreadyExistsError:
        raise exceptions.GoogleWorkspaceUserAlreadyExistsError


def _allow_to_create_billing_accounts(
    cloud_identity_creation: entities.CloudIdentityCreation,
):
    google_workspace_client = _build_google_workspace_client()

    try:
        google_workspace_client.add_user_to_group(
            cloud_identity_creation.primary_email,
            config.billing_account_creator_group_id,
        )
    except google_workspace.GroupMembershipAlreadyExistsError:
        raise exceptions.BillingCreatorGroupMembershipAlreadyExistsError


def _build_google_workspace_client() -> google_workspace.WorkspaceClient:
    # HACK: Reusing the client is not thread-safe because `googleapiclient``
    # uses httplib2 under the hood. This can be implemented later according to:
    # https://googleapis.github.io/google-api-python-client/docs/thread_safety.html
    # Every place that uses this function to build a client should instead fetch the
    # pre-built client from `config` after it's made thread-safe.
    credentials = config.service_account_credentials
    return google_workspace.WorkspaceClient(credentials=credentials)
