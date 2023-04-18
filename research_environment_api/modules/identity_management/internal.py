import sqlalchemy.exc

from research_environment_api.modules.model import db
from research_environment_api.modules.identity_management import (
    config,
    entities,
    exceptions,
    models,
    schemas,
)
from research_environment_api.modules.shared import google_workspace


def create_cloud_identity_in_google_workspace(
    cloud_identity_dto: entities.CloudIdentityCreation,
):
    google_workspace_user = entities.GoogleWorkspaceUser.from_cloud_identity(
        cloud_identity_dto
    )
    serialized_google_workspace_user = schemas.GoogleWorkspaceUser().dump(
        google_workspace_user
    )
    try:
        google_workspace.create_user(serialized_google_workspace_user)
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


def persist_cloud_identity(
    cloud_identity_dto: entities.CloudIdentityCreation,
) -> models.CloudIdentity:
    cloud_identity = models.CloudIdentity(
        primary_email=cloud_identity_dto.primary_email
    )
    db.session.add(cloud_identity)

    try:
        db.session.commit()
        return cloud_identity
    except sqlalchemy.exc.IntegrityError as e:
        db.session.rollback()
        raise exceptions.DuplicatedCloudIdentityError


def mark_cloud_identity_as_configured(
    cloud_identity_dto: entities.CloudIdentityCreation,
):
    db.session.query(models.CloudIdentity).filter(
        models.CloudIdentity.primary_email == cloud_identity_dtoprimary_email
    ).update({"is_configured": True})
    db.session.commit()
