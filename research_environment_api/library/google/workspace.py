from google.oauth2 import service_account
from googleapiclient import errors
from googleapiclient.discovery import build
from requests import Request
import os
from research_environment_api.library.google.decorators import api_request

CLOUD_RESEARCH_ENVIRONMENT_API_URL = os.environ["CLOUD_RESEARCH_ENVIRONMENTS_API_URL"]


class UserAlreadyExistsError(Exception):
    pass


class GroupMembershipAlreadyExistsError(Exception):
    pass


class ProjectAlreadyExistsError(Exception):
    pass


class ProjectsPerBillingAccountExceededError(Exception):
    pass


def create_user(credentials: service_account.Credentials, body: dict) -> dict:
    admin_service = build("admin", "directory_v1", credentials=credentials)
    try:
        created_user = admin_service.users().insert(body=body).execute()
        return created_user
    except errors.HttpError as error:
        if error.status_code == 409:
            raise UserAlreadyExistsError
        raise error


def add_user_to_group(
    credentials: service_account.Credentials, user_email: str, group_id: str
) -> dict:
    cloud_identity_service = build("cloudidentity", "v1", credentials=credentials)
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


@api_request
def create_workspace(
        gcp_user_id: str, region: str, billing_account_id: str
):
    json = {"userid": gcp_user_id, "billingid": billing_account_id, "region": region}
    request = Request("POST", url=f"{CLOUD_RESEARCH_ENVIRONMENT_API_URL}/workspace/create", json=json)
    return request


def list_workspaces(username: str):
    cloud_resource_manager = build("cloudresourcemanager", "v1")
    filtering_query = f"name:{username[:15]}* lifecycleState:ACTIVE"

    try:
        workspaces_list = cloud_resource_manager.projects().list(
            filter=filtering_query
        ).execute()
        return workspaces_list
    except errors.HttpError as error:
        raise error
