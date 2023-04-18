from research_environment_api.modules.identity_management.logger import logger
from research_environment_api.modules.identity_management import (
    entities,
    exceptions,
    internal,
)


def provision_cloud_identity(
    cloud_identity_dto: entities.CloudIdentityCreation,
) -> entities.CloudIdentityCreation:
    try:
        internal.persist_cloud_identity(cloud_identity_dto)
    except exceptions.DuplicatedCloudIdentityError:
        logger.warning(
            f"{cloud_identity_dto.primary_email} already persisted in database"
        )

    try:
        internal.create_cloud_identity_in_google_workspace(cloud_identity_dto)
    except exceptions.GoogleWorkspaceUserAlreadyExistsError:
        logger.warning(f"{cloud_identity.email} already created in Google Workspace")

    try:
        internal.allow_to_create_billing_accounts(cloud_identity_dto)
    except exceptions.BillingCreatorGroupMembershipAlreadyExistsError:
        logger.warning(
            f"{cloud_identity.email} already a member of the billing account creator group"
        )

    internal.mark_cloud_identity_as_configured(cloud_identity_dto)

    return cloud_identity
