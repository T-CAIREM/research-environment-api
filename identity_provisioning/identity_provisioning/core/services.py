import logging
from typing import Optional

from identity_provisioning import config
from identity_provisioning.core import entities, schemas, exceptions
from identity_provisioning.core.tooling import datastore, google_workspace

logger = logging.getLogger("identity_provisioning.web.app")


def provision_cloud_identity(
    google_workspace_user: entities.GoogleWorkspaceUser, password: str
) -> entities.CloudIdentity:
    cloud_identity = entities.CloudIdentity.from_google_workspace_user(google_workspace_user)
    try:
        _persist_cloud_identity(cloud_identity)
    except exceptions.CloudIdentityAlreadyExistsError:
        logger.warning(f"{cloud_identity.email} already persisted in Datastore")

    try:
        _create_cloud_identity_in_google_workspace(google_workspace_user)
    except exceptions.GoogleWorkspaceUserAlreadyExistsError:
        logger.warning(f"{google_workspace_user.primary_email} already created in Google Workspace")

    try:
        _allow_to_create_billing_accounts(cloud_identity)
    except exceptions.BillingCreatorGroupMembershipAlreadyExistsError:
        logger.warning(
            f"{cloud_identity.email} already a member of the billing account creator group"
        )

    return cloud_identity


def _persist_cloud_identity(cloud_identity: entities.CloudIdentity):
    existing_cloud_identity = _fetch_persisted_cloud_identity(cloud_identity)
    if existing_cloud_identity:
        raise exceptions.CloudIdentityAlreadyExistsError

    cloud_identity_json = schemas.CloudIdentity().dump(cloud_identity)
    datastore.persist(config.PROJECT_ID, config.DATASTORE_KIND, cloud_identity_json)


def _fetch_persisted_cloud_identity(
    cloud_identity: entities.CloudIdentity,
) -> Optional[entities.CloudIdentity]:
    query_result = list(
        datastore.find_by(
            config.PROJECT_ID, config.DATASTORE_KIND, email=cloud_identity.email
        )
    )
    result_length = len(query_result)

    if result_length > 1:
        raise exceptions.DuplicatedCloudIdentityError

    if result_length == 0:
        return None

    return schemas.CloudIdentity().load(query_result[0])


def _create_cloud_identity_in_google_workspace(google_workspace_user: entities.GoogleWorkspaceUser):
    serialized_google_workspace_user = schemas.GoogleWorkspaceUser().dump(
        google_workspace_user
    )
    try:
        google_workspace.create_user(serialized_google_workspace_user)
    except google_workspace.UserAlreadyExistsError:
        raise exceptions.GoogleWorkspaceUserAlreadyExistsError

    return google_workspace_user


def _allow_to_create_billing_accounts(cloud_identity: entities.CloudIdentity):
    try:
        google_workspace.add_user_to_group(
            cloud_identity.email, config.BILLING_ACCOUNT_CREATOR_GROUP_ID
        )
    except google_workspace.GroupMembershipAlreadyExistsError:
        raise exceptions.BillingCreatorGroupMembershipAlreadyExistsError
