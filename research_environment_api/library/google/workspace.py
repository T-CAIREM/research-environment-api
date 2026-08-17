from google.oauth2 import service_account
from googleapiclient import errors
from googleapiclient.discovery import build


class UserAlreadyExistsError(Exception):
    description = "User already exists in organization"
    pass


class GroupMembershipAlreadyExistsError(Exception):
    description = "User has already been added to group"
    pass


class WorkspaceAuthorizationError(Exception):
    description = (
        "Not authorized to call Google Workspace. The service account needs a "
        "Workspace admin role assigned to it directly (Admin console > Account > "
        "Admin roles > Assign service accounts); GCP project IAM grants no "
        "Workspace privileges"
    )
    pass


class WorkspaceClient:
    def __init__(self, credentials: service_account.Credentials):
        self.admin_directory_client = build(
            "admin", "directory_v1", credentials=credentials
        )
        self.cloud_identity_client = build(
            "cloudidentity", "v1", credentials=credentials
        )

    def create_user(self, body: dict) -> dict:
        try:
            created_user = (
                self.admin_directory_client.users().insert(body=body).execute()
            )
            return created_user
        except errors.HttpError as error:
            if error.status_code == 409:
                raise UserAlreadyExistsError
            if error.status_code in (401, 403):
                raise WorkspaceAuthorizationError from error
            raise error

    def add_user_to_group(self, user_email: str, group_id: str) -> dict:
        body = {"preferredMemberKey": {"id": user_email}, "roles": {"name": "MEMBER"}}
        group_id = f"groups/{group_id}"
        try:
            # https://googleapis.github.io/google-api-python-client/docs/dyn/cloudidentity_v1.groups.memberships.html#create
            created_policy = (
                self.cloud_identity_client.groups()
                .memberships()
                .create(parent=group_id, body=body)
                .execute()
            )
            return created_policy
        except errors.HttpError as error:
            if error.status_code == 409:
                raise GroupMembershipAlreadyExistsError
            if error.status_code in (401, 403):
                raise WorkspaceAuthorizationError from error
            raise error
