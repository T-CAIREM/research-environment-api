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

    dataset_identifier = workbench_creation_request.dataset_identifier
    instance_name = f"jupyter-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    service_account_name = f"jupyter-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"

    build = builds.create_jupyter_workbench_build(
        workspace_project_id=workbench_creation_request.workspace_project_id,
        instance_name=instance_name,
        service_account_name=service_account_name,
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
                build_type=enums.BuildType.WORKBENCH_CREATION,
                invoker_email=workbench_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workspace_id=workbench_creation_request.workspace_project_id,
                workbench_id=instance_name,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.create_jupyter_workbench(
                build=build,
                user_email=workbench_creation_request.user_email,
                workspace_project_id=workbench_creation_request.workspace_project_id,
                instance_zone=zone,
                instance_name=instance_name,
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
                workspace_id=workspace_creation_request.workspace_project_id,
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
                workspace_id=workspace_deletion_request.workspace_project_id,
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
        gcp_project_id=workbench_stop_request.workspace_project_id,
        workbench_name=workbench_stop_request.workbench_resource_id,
        user_email=workbench_stop_request.user_email,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.WORKBENCH_STOP,
                invoker_email=workbench_stop_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workbench_id=gce_instance.gcp_identifier,
                workspace_id=workbench_stop_request.workspace_project_id,
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
        gcp_project_id=workbench_start_request.workspace_project_id,
        workbench_name=workbench_start_request.workbench_resource_id,
        user_email=workbench_start_request.user_email,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_type=enums.BuildType.WORKBENCH_START,
                invoker_email=workbench_start_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workbench_id=gce_instance.gcp_identifier,
                workspace_id=workbench_start_request.workspace_project_id,
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
        gcp_project_id=workbench_update_request.workspace_project_id,
        workbench_name=workbench_update_request.workbench_resource_id,
        user_email=workbench_update_request.user_email,
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
                build_type=enums.BuildType.WORKBENCH_UPDATE,
                invoker_email=workbench_update_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workbench_id=gce_instance.gcp_identifier,
                workspace_id=workbench_update_request.workspace_project_id,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.update_jupyter_workbench(
                build=build,
                workspace_project_id=workbench_update_request.workspace_project_id,
                instance_zone=gce_instance.zone,
                instance_name=workbench_update_request.workbench_resource_id,
                user_email=workbench_update_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def destroy_jupyter_workbench(
    workbench_destroy_request: entities.WorkbenchDestroy,
) -> uuid.UUID:
    gce_instance = services.get_jupyter_workbench(
        gcp_project_id=workbench_destroy_request.workspace_project_id,
        workbench_name=workbench_destroy_request.workbench_resource_id,
        user_email=workbench_destroy_request.user_email,
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
                build_type=enums.BuildType.WORKBENCH_DESTROY,
                invoker_email=workbench_destroy_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workbench_id=gce_instance.gcp_identifier,
                workspace_id=workbench_destroy_request.workspace_project_id,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.destroy_jupyter_workbench(
                build=build,
                user_email=workbench_destroy_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def create_rstudio_workbench(
    workbench_creation_request: entities.WorkbenchCreate,
) -> uuid.UUID:
    dataset_identifier = workbench_creation_request.dataset_identifier
    instance_name = f"rstudio-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    service_account_name = f"rstudio-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"

    build = builds.create_rstudio_workbench_build(
        workspace_project_id=workbench_creation_request.workspace_project_id,
        region=workbench_creation_request.region.value,
        machine_type=workbench_creation_request.machine_type,
        disk_size=workbench_creation_request.disk_size,
        dataset_identifier=workbench_creation_request.dataset_identifier,
        user_email=workbench_creation_request.user_email,
        bucket_name=workbench_creation_request.bucket_name,
        instance_name=instance_name,
        service_account_name=service_account_name,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workspace_id=workbench_creation_request.workspace_project_id,
                workbench_id=instance_name,
                build_type=enums.BuildType.WORKBENCH_CREATION,
                invoker_email=workbench_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.create_rstudio_workbench(
                build=build,
                user_email=workbench_creation_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def stop_rstudio_workbench(
    workbench_stop_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    build = builds.stop_rstudio_workbench_build(
        workspace_project_id=workbench_stop_request.workspace_project_id,
        workbench_resource_id=workbench_stop_request.workbench_resource_id,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workspace_id=workbench_stop_request.workspace_project_id,
                workbench_id=workbench_stop_request.workbench_resource_id,
                build_type=enums.BuildType.WORKBENCH_STOP,
                invoker_email=workbench_stop_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.stop_rstudio_workbench(
                build=build,
                user_email=workbench_stop_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def start_rstudio_workbench(
    workbench_start_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    build = builds.start_rstudio_workbench_build(
        workspace_project_id=workbench_start_request.workspace_project_id,
        workbench_resource_id=workbench_start_request.workbench_resource_id,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workspace_id=workbench_start_request.workspace_project_id,
                workbench_id=workbench_start_request.workbench_resource_id,
                build_type=enums.BuildType.WORKBENCH_START,
                invoker_email=workbench_start_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.start_rstudio_workbench(
                build=build,
                user_email=workbench_start_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def update_rstudio_workbench(
    workbench_update_request: entities.WorkbenchUpdate,
) -> uuid.UUID:
    app_engine_instance = services.get_rstudio_workbench(
        workbench_update_request.workspace_project_id,
        workbench_update_request.workbench_resource_id,
        workbench_update_request.user_email,
    )

    build = builds.update_rstudio_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        region=app_engine_instance.region,
        machine_type=workbench_update_request.machine_type,
        disk_size=app_engine_instance.disk_size,
        dataset_identifier=app_engine_instance.dataset_identifier,
        user_email=workbench_update_request.user_email,
        instance_name=app_engine_instance.name,
        service_account_name=app_engine_instance.service_account_name,
        workbench_id=workbench_update_request.workbench_resource_id,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workspace_id=workbench_update_request.workspace_project_id,
                workbench_id=workbench_update_request.workbench_resource_id,
                build_type=enums.BuildType.WORKBENCH_UPDATE,
                invoker_email=workbench_update_request.user_email,
                id=uuid.uuid4(),
            )
            session.add(workbench_activity)

            workflows.update_rstudio_workbench(
                build=build,
                user_email=workbench_update_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def destroy_rstudio_workbench(
    workbench_destroy_request: entities.WorkbenchDestroy,
) -> uuid.UUID:
    app_engine_instance = services.get_rstudio_workbench(
        workbench_destroy_request.workspace_project_id,
        workbench_destroy_request.workbench_resource_id,
        workbench_destroy_request.user_email,
    )

    build = builds.destroy_rstudio_workbench_build(
        workspace_project_id=workbench_destroy_request.workspace_project_id,
        user_email=workbench_destroy_request.user_email,
        instance_name=app_engine_instance.name,
        bucket_name=app_engine_instance.bucket_name,
        dataset_identifier=app_engine_instance.dataset_identifier,
        disk_size=app_engine_instance.disk_size,
        machine_type=app_engine_instance.machine_type,
        service_account_name=app_engine_instance.service_account_name,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workspace_id=workbench_destroy_request.workspace_project_id,
                workbench_id=workbench_destroy_request.workbench_resource_id,
                build_type=enums.BuildType.WORKBENCH_DESTROY,
                invoker_email=workbench_destroy_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.destroy_rstudio_workbench(
                build=build,
                user_email=workbench_destroy_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id
