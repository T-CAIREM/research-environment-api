import random

from research_environment_api.background import builds, constants, workflows, enums
from research_environment_api.modules.workbench_management import (
    entities as workbench_entities,
)
from research_environment_api.modules.workbench_management import services, models
from research_environment_api.modules.workspace_management import (
    entities as workspace_entities,
)
from research_environment_api.modules.app import app


def create_jupyter_notebook(
    workbench_creation_request: workbench_entities.WorkbenchCreate,
):
    zones = constants.AVAILABLE_ZONES[workbench_creation_request.region.value]
    zone, *fallback_zones = random.sample(zones, len(zones))

    build = builds.create_jupyter_workbench_build(
        workspace_project_id=workbench_creation_request.workspace_project_id,
        region=workbench_creation_request.region.value,
        zone=zone,
        machine_type=workbench_creation_request.machine_type,
        persistent_disk=workbench_creation_request.persistent_disk,
        gpu_accelerator_type=workbench_creation_request.gpu_accelerator_type,
        dataset_identifier=workbench_creation_request.dataset_identifier,
        user_email=workbench_creation_request.user_email,
        bucket_name=workbench_creation_request.bucket_name,
        vm_image=workbench_creation_request.vm_image,
        jupyter_startup_script_bucket=workbench_creation_request.jupyter_startup_script_bucket,
    )

    workbench_activity = models.WorkbenchActivity(
        build_type=enums.BuildType.JUPYTER_CREATION,
        invoker_email=workbench_creation_request.user_email,
        build_status=enums.WorkflowStatus.IN_PROGRESS
    )

    workflows.create_jupyter_notebook(
        build=build,
        user_email=workbench_creation_request.user_email,
        fallback_zones=fallback_zones,
        workbench_activity_id=workbench_activity.id
    )()

    with app.database_session() as session:
        session.add(workbench_activity)
        session.commit()

    return workbench_activity.id


def create_workspace(
    workspace_creation_request: workspace_entities.WorkspaceCreation,
):
    build = builds.create_workspace_build(
        billing_account_id=workspace_creation_request.billing_account_id,
        workspace_project_id=workspace_creation_request.workspace_project_id,
        user_email=workspace_creation_request.user_email,
        region=workspace_creation_request.region.value,
    )

    workbench_activity = models.WorkbenchActivity(
        build_type=enums.BuildType.WORKSPACE_CREATION,
        invoker_email=workspace_creation_request.user_email,
        build_status=enums.WorkflowStatus.IN_PROGRESS
    )

    workflows.create_workspace(
        build=build, user_email=workspace_creation_request.user_email
    )()

    with app.database_session() as session:
        session.add(workbench_activity)
        session.commit()

    return workbench_activity.id


def destroy_workspace(workspace_deletion_request: workspace_entities.WorkspaceDeletion):
    build = builds.destroy_workspace_build(
        billing_account_id=workspace_deletion_request.billing_account_id,
        workspace_project_id=workspace_deletion_request.workspace_project_id,
        user_email=workspace_deletion_request.user_email,
        region=workspace_deletion_request.region.value,
    )

    workbench_activity = models.WorkbenchActivity(
        build_type=enums.BuildType.WORKSPACE_DELETION,
        invoker_email=workspace_deletion_request.user_email,
        build_status=enums.WorkflowStatus.IN_PROGRESS
    )
    with app.database_session() as session:
        session.add(workbench_activity)
        session.commit()

    workflows.destroy_workspace(
        build=build, user_email=workspace_deletion_request.user_email, workbench_activity_id=workbench_activity.id
    )()

    return workbench_activity.id


def stop_jupyter_workbench(
    workbench_stop_request: workbench_entities.WorkbenchStartStop,
):
    gce_instance = services.get_jupyter_workbench(
        workbench_resource_id=workbench_stop_request.workbench_resource_id,
        gcp_project_id=workbench_stop_request.workspace_project_id,
    )
    workbench_activity = models.WorkbenchActivity(
        build_type=enums.BuildType.JUPYTER_STOP,
        invoker_email=workbench_stop_request.user_email,
        build_status=enums.WorkflowStatus.IN_PROGRESS
    )

    workflows.stop_jupyter_workbench(
        workspace_project_id=workbench_stop_request.workspace_project_id,
        workbench_resource_id=workbench_stop_request.workbench_resource_id,
        instance_zone=gce_instance.zone,
        workbench_activity_id=workbench_activity.id
    )()

    with app.database_session() as session:
        session.add(workbench_activity)
        session.commit()

    return workbench_activity.id


def start_jupyter_workbench(
    workbench_start_request: workbench_entities.WorkbenchStartStop,
):
    gce_instance = services.get_jupyter_workbench(
        workbench_resource_id=workbench_start_request.workbench_resource_id,
        gcp_project_id=workbench_start_request.workspace_project_id,
    )

    workbench_activity = models.WorkbenchActivity(
        build_type=enums.BuildType.JUPYTER_START,
        invoker_email=workbench_start_request.user_email,
        build_status=enums.WorkflowStatus.IN_PROGRESS
    )
    with app.database_session() as session:
        session.add(workbench_activity)
        session.commit()

    workflows.start_jupyter_workbench(
        workspace_project_id=workbench_start_request.workspace_project_id,
        workbench_resource_id=workbench_start_request.workbench_resource_id,
        instance_zone=gce_instance.zone,
        workbench_activity_id=workbench_activity.id
    )()

    return workbench_activity.id


def update_jupyter_workbench(
    workbench_update_request: workbench_entities.WorkbenchUpdate,
):
    gce_instance = services.get_jupyter_workbench(
        workbench_resource_id=workbench_update_request.workbench_resource_id,
        gcp_project_id=workbench_update_request.workspace_project_id,
    )
    build = builds.update_jupyter_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        region=workbench_update_request.region.value,
        machine_type=workbench_update_request.machine_type,
        persistent_disk=workbench_update_request.persistent_disk,
        gpu_accelerator_type=workbench_update_request.gpu_accelerator_type,
        dataset_identifier=workbench_update_request.dataset_identifier,
        user_email=workbench_update_request.user_email,
        bucket_name=workbench_update_request.bucket_name,
        vm_image=workbench_update_request.vm_image,
        jupyter_startup_script_bucket=workbench_update_request.jupyter_startup_script_bucket,
        workbench_resource_id=workbench_update_request.workbench_resource_id,
        zone=gce_instance.zone,
    )

    workbench_activity = models.WorkbenchActivity(
        build_type=enums.BuildType.JUPYTER_UPDATE,
        invoker_email=workbench_update_request.user_email,
        build_status=enums.WorkflowStatus.IN_PROGRESS
    )
    with app.database_session() as session:
        session.add(workbench_activity)
        session.commit()

    workflows.update_jupyter_workbench(
        build=build, user_email=workbench_update_request.user_email, workbench_activity_id=workbench_activity.id
    )()

    return workbench_activity.id
