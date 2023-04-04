import google.auth
from googleapiclient import errors
from googleapiclient.discovery import build


class UserAlreadyExistsError(Exception):
    pass


class GroupMembershipAlreadyExistsError(Exception):
    pass


def create_user(body: dict) -> dict:
    admin_service = build("admin", "directory_v1")
    try:
        created_user = admin_service.users().insert(body=body).execute()
        return created_user
    except errors.HttpError as error:
        if error.status_code == 409:
            raise UserAlreadyExistsError
        raise error


def reset_user_password(user_key: str, body: dict) -> dict:
    admin_service = build("admin", "directory_v1")
    try:
        updated_user = admin_service.users().update(userKey=user_key, body=body).execute()
        return updated_user
    except errors.HttpError as error:
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
            raise GroupMembershipAlreadyExistsError
