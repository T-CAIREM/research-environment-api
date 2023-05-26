from research_environment_api.modules.logger import logger
from research_environment_api.modules.identity_management import (
    entities,
    exceptions,
    internal,
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
        internal.create_cloud_identity_in_google_workspace(cloud_identity_creation)
    except exceptions.GoogleWorkspaceUserAlreadyExistsError:
        logger.warning(
            f"{cloud_identity_creation.primary_email} already created in Google Workspace"
        )


def _allow_to_create_billing_accounts(cloud_identity_creation):
    try:
        internal.allow_to_create_billing_accounts(cloud_identity_creation)
    except exceptions.BillingCreatorGroupMembershipAlreadyExistsError:
        logger.warning(
            f"{cloud_identity_creation.primary_email} already a member of the billing account creator group"
        )
