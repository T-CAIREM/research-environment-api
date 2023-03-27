import json
from typing import Optional

import config
import entities
import schemas
import exceptions
from lib import datastore, secret_manager, google_workspace


def provision_cloud_identity(cloud_identity: entities.CloudIdentity):
    try:
        _persist_cloud_identity(cloud_identity)
    except exceptions.CloudIdentityAlreadyExistsError:
        print("Cloud Identity alread in Datastoer")
        pass

    try:
        _create_cloud_identity_in_google_workspace(cloud_identity)
    except exceptions.GoogleWorkspaceUserAlreadyExistsError:
        print("Yser Exists")
        pass

    _allow_to_create_billing_accounts(cloud_identity)

    return cloud_identity


def _create_cloud_identity_in_google_workspace(cloud_identity: entities.CloudIdentity):
    service_account_secret = json.loads(
        secret_manager.fetch_secret(config.PROJECT_ID, "cloud-identity-secret", 1)
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
    try:
        google_workspace.create_user(
            google_admin_credentials, serialized_google_workspace_user
        )
    except google_workspace.UserAlreadyExistsError:
        raise exceptions.GoogleWorkspaceUserAlreadyExistsError

    return cloud_identity


def _allow_to_create_billing_accounts(cloud_identity: entities.CloudIdentity):
    google_workspace.add_user_to_group(
        cloud_identity.email, config.BILLING_ACCOUNT_CREATOR_GROUP_ID
    )


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
