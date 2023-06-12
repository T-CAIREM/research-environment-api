import google_auth_httplib2
import httplib2
from google.oauth2 import service_account
from googleapiclient import errors
from googleapiclient.discovery import build


class UserAlreadyExistsError(Exception):
    pass


class GroupMembershipAlreadyExistsError(Exception):
    pass


class WorkspaceClient:
    def __init__(self, credentials: service_account.Credentials):
        # Ensure thread-safety: https://googleapis.github.io/google-api-python-client/docs/thread_safety.html
        admin_directory_authorized_http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http())
        self.admin_directory_client = build(
            "admin", "directory_v1", http=admin_directory_authorized_http,
        )

        # Ensure thread-safety: https://googleapis.github.io/google-api-python-client/docs/thread_safety.html
        cloud_identity_authorized_http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http())
        self.cloud_identity_client = build(
            "cloudidentity", "v1", http=cloud_identity_authorized_http,
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
            raise error

    def add_user_to_group(self, user_email: str, group_id: str) -> dict:
        body = {"preferredMemberKey": {"id": user_email}, "roles": {"name": "MEMBER"}}
        group_id = f"groups/{group_id}"
        try:
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
            raise error
