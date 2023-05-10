from google.oauth2 import service_account
from googleapiclient import errors
from googleapiclient.discovery import build
from google.cloud.devtools import cloudbuild_v1


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


def create_workspace(project_name: str, region: str):
    cloud_build_service = build("cloudbuild", "v1")
    parent_path = f"projects/{project_name}/locations/{region}"

    try:
        created_project = cloud_build_service.projects().locations().builds().create(
            projectId=project_name, parent=parent_path
        )
        return created_project
    except errors.HttpError as error:
        if error.status_code == 409:
            raise ProjectAlreadyExistsError


def attach_billing_to_project(project_name: str, billing_account_resource_name: str):
    cloud_build_service = build("cloudbuild", "v1")
    project_path = f"projects/{project_name}"
    body = {"billingAccountName": f"billingAccounts/{billing_account_resource_name}"}

    try:
        project_billing_info = cloud_build_service.projects().updateBillingInfo(
            name=project_path, body=body
        )
        return project_billing_info
    except errors.HttpError as error:
        if error.status_code == 429:
            raise ProjectsPerBillingAccountExceededError


def list_workspaces(family_name: str):
    cloud_resource_manager = build("cloudresourcemanager", "v1")
    filtering_query = f"name:{family_name[:15]}* lifecycleState:ACTIVE"

    try:
        workspaces_list = cloud_resource_manager.projects().list(
            filter=filtering_query
        )
        return workspaces_list
    except errors.HttpError as error:
        raise error
