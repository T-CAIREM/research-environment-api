from googleapiclient import errors
from googleapiclient.discovery import build


def list_workspaces(username: str):
    cloud_resource_manager = build("cloudresourcemanager", "v1")
    filtering_query = f"name:{username[:15]}* lifecycleState:ACTIVE"

    try:
        workspaces_list = (
            cloud_resource_manager.projects().list(filter=filtering_query).execute()
        )
        return workspaces_list
    except errors.HttpError as error:
        raise error
