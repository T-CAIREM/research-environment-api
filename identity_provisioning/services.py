from typing import Optional

import config
import entities
import schemas
import enums
import exceptions
from lib import datastore, secret_manager, google_workspace


def provision_cloud_identity(new_cloud_identity: entities.CloudIdentity):
    cloud_identity = _recover_or_persist_cloud_identity(new_cloud_identity)
    if cloud_identity.is_initial:
        cloud_identity = _create_cloud_identity_in_google_workspace(cloud_identity)

    if cloud_identity.is_created_in_workspace:
        cloud_identity = _allow_to_create_billing_accounts_billing_account_creator_role(
            cloud_identity
        )

    return cloud_identity


def _recover_or_persist_cloud_identity(
    new_cloud_identity: entities.CloudIdentity,
) -> entities.CloudIdentity:
    existing_cloud_identity = _fetch_persisted_cloud_identity(new_cloud_identity)
    if existing_cloud_identity:
        return existing_cloud_identity

    _persist_cloud_identity(new_cloud_identity)
    return new_cloud_identity


def _create_cloud_identity_in_google_workspace(cloud_identity: entities.CloudIdentity):
    service_account_secret = secret_manager.fetch_secret(
        config.PROJECT_ID, "cloud-identity-secret", 1
    )
    google_admin_credentials = google_workspace.build_service_account_credentials(
        service_account_secret
    )
    google_workspace_user = entities.GoogleWorkspaceUser.from_cloud_identity(
        cloud_identity
    )
    serialized_google_workspace_user = schemas.GoogleWorkspaceUser().dump(
        google_workspace_user
    )
    google_workspace.create_user(
        google_admin_credentials, serialized_google_workspace_user
    )
    _update_cloud_identity_provisioning_status(
        cloud_identity, enums.CloudIdentityProvisioningStatus.CREATED_IN_WORKSPACE
    )
    return cloud_identity


def _allow_to_create_billing_accounts(cloud_identity: entities.CloudIdentity):
    lib.add_user_to_group(cloud_identity.email, config.BILLING_ACCOUNT_CREATOR_GROUP_ID)
    _update_cloud_identity_provisioning_status(
        cloud_identity, enums.CloudIdentityProvisioningStatus.PROVISIONED
    )
    return cloud_identity


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


def _persist_cloud_identity(cloud_identity: entities.CloudIdentity):
    cloud_identity_json = schemas.CloudIdentity().dump(cloud_identity)
    return datastore.persist(
        config.PROJECT_ID, config.DATASTORE_KIND, cloud_identity_json
    )


def _update_cloud_identity_provisioning_status(
    cloud_identity: entities.CloudIdentity,
    status: enums.CloudIdentityProvisioningStatus,
):
    pass
