import google.auth
from googleapiclient import errors
from googleapiclient.discovery import build


class UserAlreadyExistsError(Exception):
    pass


class MembershipAlreadyExistsError(Exception):
    pass


def create_user(body: dict) -> dict:
    admin_service = build(
        "admin",
        "directory_v1",
        client_options={
            "scopes": ["https://www.googleapis.com/auth/admin.directory.user"]
        },
    )
    try:
        created_user = admin_service.users().insert(body=body).execute()
        return created_user
    except errors.HttpError as error:
        if error.status_code == 409:
            raise UserAlreadyExistsError
        raise error


def add_user_to_group(user_email: str, group_id: str) -> dict:
    cloud_identity_service = build("cloudidentity", "v1")
    body = {"preferredMemberKey": {"id": user_email}, "roles": {"name": "MEMBER"}}
    group_id = f"groups/{group_id}"
    try:
        created_policy = (
            cloud_identity_service.groups()
            .memberships()
            .create(parent=group_id, body=body)
            .execute()
        )
        return created_policy
    except errors.HttpError as error:
        if error.status_code == 409:
            raise MembershipAlreadyExistsError
        raise error
