import random

from research_environment_api.background import builds, constants, workflows
from research_environment_api.modules.workbench_management import (
    entities as workbench_entities,
)
from research_environment_api.modules.workspace_management import (
    entities as workspace_entities,
)


def create_jupyter_notebook(
    workbench_creation_request: workbench_entities.WorkbenchCreation,
):
    zones = constants.AVAILABLE_ZONES[workbench_creation_request.region]
    zone, *fallback_zones = random.sample(zones, len(zones))

    build = builds.create_jupyter_workbench_build(
        zone=zone, **workbench_creation_request
    )
    return workflows.create_jupyter_notebook(
        build=build,
        user_email=workbench_creation_request.email_id,
        fallback_zones=fallback_zones,
    )()


def stop_jupyter_workbench(workbench_stop_request: workbench_entities.WorkbenchStop):
    return workflows.stop_jupyter_workbench(**workbench_stop_request)()


def create_workspace(
    workspace_creation_request: workspace_entities.WorkspaceCreation,
):
    build = builds.create_workspace_build(**workspace_creation_request)
    return workflows.create_workspace(
        build=build, user_email=workspace_creation_request.email_id
    )


def destroy_workspace(workspace_deletion_request: workspace_entities.WorkspaceDeletion):
    build = builds.destroy_workspace_build(**workspace_deletion_request)
    return workflows.destroy_workspace(
        build=build, user_email=workspace_deletion_request.email_id
    )
