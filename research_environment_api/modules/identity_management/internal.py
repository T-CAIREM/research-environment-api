from typing import Optional

from research_environment_api.modules import config

from research_environment_api.modules.identity_management import (
    entities,
    exceptions,
)
from research_environment_api.library.google import workspace as google_workspace


def create_cloud_identity_in_google_workspace(
    cloud_identity_dto: entities.CloudIdentityCreation,
):
    google_workspace_user = {
        "name": {
            "givenName": cloud_identity_dto.given_name,
            "familyName": cloud_identity_dto.family_name,
        },
        "primaryEmail": cloud_identity_dto.primary_email,
        "recoveryEmail": cloud_identity_dto.recovery_email,
        "password": cloud_identity_dto.password,
    }

    try:
        google_workspace.create_user(
            config.app_config().service_account_credentials, google_workspace_user
        )
    except google_workspace.UserAlreadyExistsError:
        raise exceptions.GoogleWorkspaceUserAlreadyExistsError


def allow_to_create_billing_accounts(
    cloud_identity_dto: entities.CloudIdentityCreation,
):
    try:
        google_workspace.add_user_to_group(
            config.app_config().service_account_credentials,
            cloud_identity_dto.primary_email,
            config.app_config().billing_account_creator_group_id,
        )
    except google_workspace.GroupMembershipAlreadyExistsError:
        raise exceptions.BillingCreatorGroupMembershipAlreadyExistsError
