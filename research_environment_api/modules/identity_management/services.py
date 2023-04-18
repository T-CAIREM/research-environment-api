from research_environment_api.modules.logger import logger
from research_environment_api.modules.identity_management import (
    entities,
    exceptions,
    internal,
)


def provision_cloud_identity(
    cloud_identity_dto: entities.CloudIdentityCreation,
) -> entities.CloudIdentityCreation:
    cloud_identity = internal.fetch_cloud_identity(cloud_identity_dto)

    if cloud_identity and cloud_identity.is_configured:
        raise exceptions.CloudIdentityAlreadyConfiguredError()

    if not cloud_identity:
        cloud_identity = internal.persist_cloud_identity(cloud_identity_dto)

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

    internal.mark_cloud_identity_as_configured(cloud_identity)

    return cloud_identity_dto
