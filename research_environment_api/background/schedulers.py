import random
import uuid

from research_environment_api.background import builds, constants, enums, workflows
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import (
    entities,
    models,
    services,
)


def create_jupyter_workbench(
    workbench_creation_request: entities.WorkbenchCreate,
) -> uuid.UUID:
    zones = constants.AVAILABLE_ZONES[workbench_creation_request.region]
    zone, *fallback_zones = random.sample(zones, len(zones))

    build = builds.create_jupyter_workbench_build(
        workspace_project_id=workbench_creation_request.workspace_project_id,
        region=workbench_creation_request.region,
        zone=zone,
        machine_type=workbench_creation_request.machine_type,
        disk_size=workbench_creation_request.disk_size,
        gpu_accelerator_type=workbench_creation_request.gpu_accelerator_type,
        dataset_identifier=workbench_creation_request.dataset_identifier,
        user_email=workbench_creation_request.user_email,
        bucket_name=workbench_creation_request.bucket_name,
        vm_image=workbench_creation_request.vm_image,
        jupyter_startup_script_bucket=workbench_creation_request.jupyter_startup_script_bucket,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.JUPYTER_CREATION,
                invoker_email=workbench_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.create_jupyter_workbench(
                build=build,
                user_email=workbench_creation_request.user_email,
                fallback_zones=fallback_zones,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def create_workspace(
    workspace_creation_request: entities.WorkspaceCreation,
) -> uuid.UUID:
    build = builds.create_workspace_build(
        billing_account_id=workspace_creation_request.billing_account_id,
        workspace_project_id=workspace_creation_request.workspace_project_id,
        user_email=workspace_creation_request.user_email,
        region=workspace_creation_request.region,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.WORKSPACE_CREATION,
                invoker_email=workspace_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.create_workspace(
                build=build,
                user_email=workspace_creation_request.user_email,
                workbench_activity_id=workbench_activity.id,
                workspace_project_id=workspace_creation_request.workspace_project_id,
            )()

            return workbench_activity.id


def destroy_workspace(
    workspace_deletion_request: entities.WorkspaceDeletion,
) -> uuid.UUID:
    build = builds.destroy_workspace_build(
        billing_account_id=workspace_deletion_request.billing_account_id,
        workspace_project_id=workspace_deletion_request.workspace_project_id,
        user_email=workspace_deletion_request.user_email,
        region=workspace_deletion_request.region,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.WORKSPACE_DELETION,
                invoker_email=workspace_deletion_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.destroy_workspace(
                build=build,
                user_email=workspace_deletion_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def stop_jupyter_workbench(
    workbench_stop_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    gce_instance = services.get_jupyter_workbench(
        workbench_resource_id=workbench_stop_request.workbench_resource_id,
        gcp_project_id=workbench_stop_request.workspace_project_id,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.JUPYTER_STOP,
                invoker_email=workbench_stop_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.stop_jupyter_workbench(
                workspace_project_id=workbench_stop_request.workspace_project_id,
                workbench_resource_id=workbench_stop_request.workbench_resource_id,
                instance_zone=gce_instance.zone,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def start_jupyter_workbench(
    workbench_start_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    gce_instance = services.get_jupyter_workbench(
        workbench_resource_id=workbench_start_request.workbench_resource_id,
        gcp_project_id=workbench_start_request.workspace_project_id,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.JUPYTER_START,
                invoker_email=workbench_start_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.start_jupyter_workbench(
                workspace_project_id=workbench_start_request.workspace_project_id,
                workbench_resource_id=workbench_start_request.workbench_resource_id,
                instance_zone=gce_instance.zone,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def update_jupyter_workbench(
    workbench_update_request: entities.WorkbenchUpdate,
) -> uuid.UUID:
    gce_instance = services.get_jupyter_workbench(
        workbench_resource_id=workbench_update_request.workbench_resource_id,
        gcp_project_id=workbench_update_request.workspace_project_id,
    )
    build = builds.update_jupyter_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        workbench_name=gce_instance.name,
        machine_type=workbench_update_request.machine_type,
        user_email=workbench_update_request.user_email,
        region=gce_instance.region,
        disk_size=gce_instance.disk_size,
        gpu_accelerator_type=gce_instance.gpu_accelerator_type,
        dataset_identifier=gce_instance.dataset_identifier,
        bucket_name=gce_instance.bucket_name,
        zone=gce_instance.zone,
        vm_image=gce_instance.vm_image,
        jupyter_startup_script_bucket=workbench_update_request.jupyter_startup_script_bucket,
        service_account_name=gce_instance.service_account_name,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.JUPYTER_UPDATE,
                invoker_email=workbench_update_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.update_jupyter_workbench(
                build=build,
                user_email=workbench_update_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def destroy_jupyter_workbench(
    workbench_destroy_request: entities.WorkbenchDestroy,
) -> uuid.UUID:
    gce_instance = services.get_jupyter_workbench(
        workbench_resource_id=workbench_destroy_request.workbench_resource_id,
        gcp_project_id=workbench_destroy_request.workspace_project_id,
    )
    build = builds.destroy_jupyter_workbench_build(
        workspace_project_id=workbench_destroy_request.workspace_project_id,
        workbench_name=gce_instance.name,
        user_email=workbench_destroy_request.user_email,
        region=gce_instance.region,
        machine_type=gce_instance.machine_type,
        disk_size=gce_instance.disk_size,
        gpu_accelerator_type=gce_instance.gpu_accelerator_type,
        dataset_identifier=gce_instance.dataset_identifier,
        bucket_name=gce_instance.bucket_name,
        zone=gce_instance.zone,
        vm_image=gce_instance.vm_image,
        jupyter_startup_script_bucket=workbench_destroy_request.jupyter_startup_script_bucket,
        service_account_name=gce_instance.service_account_name,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.JUPYTER_DESTROY,
                invoker_email=workbench_destroy_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.destroy_jupyter_workbench(
                build=build,
                user_email=workbench_destroy_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id
