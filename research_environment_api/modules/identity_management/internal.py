from typing import Optional

import sqlalchemy.exc

from research_environment_api.modules.model import db
from research_environment_api.modules.identity_management import (
    config,
    entities,
    exceptions,
    models,
)
from research_environment_api.library.google import workspace as google_workspace


def fetch_cloud_identity(
    cloud_identity_dto: entities.CloudIdentityCreation,
) -> Optional[models.CloudIdentity]:
    try:
        return (
            db.session.query(models.CloudIdentity)
            .filter_by(primary_email=cloud_identity_dto.primary_email)
            .one()
        )
    except sqlalchemy.exc.NoResultFound:
        return None


def persist_cloud_identity(
    cloud_identity_dto: entities.CloudIdentityCreation,
) -> models.CloudIdentity:
    cloud_identity = models.CloudIdentity(
        primary_email=cloud_identity_dto.primary_email
    )
    db.session.add(cloud_identity)
    db.session.commit()

    return cloud_identity


def mark_cloud_identity_as_configured(
    cloud_identity: models.CloudIdentity,
):
    cloud_identity.is_configured = True
    db.session.commit()


def create_cloud_identity_in_google_workspace(
    cloud_identity_dto: entities.CloudIdentityCreation,
):
    google_workspace_user = {
        "name": {
            "givenName": cloud_identity_dto.given_name,
            "familyName": cloud_identity_dto.family_name,
        },
        "primaryEmail": cloud_identity_dto.recovery_email,
        "recoveryEmail": cloud_identity_dto.recovery_email,
        "password": cloud_identity_dto.password,
    }

    try:
        google_workspace.create_user(google_workspace_user)
    except google_workspace.UserAlreadyExistsError:
        raise exceptions.GoogleWorkspaceUserAlreadyExistsError


def allow_to_create_billing_accounts(
    cloud_identity_dto: entities.CloudIdentityCreation,
):
    try:
        google_workspace.add_user_to_group(
            cloud_identity_dto.primary_email, config.BILLING_ACCOUNT_CREATOR_GROUP_ID
        )
    except google_workspace.GroupMembershipAlreadyExistsError:
        raise exceptions.BillingCreatorGroupMembershipAlreadyExistsError
