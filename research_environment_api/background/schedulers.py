import random
import uuid

from research_environment_api.background import builds, enums, workflows
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import (
    entities,
    models,
    services,
)


def create_jupyter_workbench(
    workbench_creation_request: entities.WorkbenchCreate,
) -> uuid.UUID:
    zone, *fallback_zones = services.get_available_zones(
        workbench_creation_request.region
    )

    dataset_identifier = workbench_creation_request.dataset_identifier
    workbench_id = f"jupyter-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    service_account_name = f"jupyter-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"

    build = builds.create_jupyter_workbench_build(
        instance_name=workbench_id,
        workspace_project_id=workbench_creation_request.workspace_project_id,
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
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                build_type=enums.BuildType.WORKBENCH_CREATION,
                invoker_email=workbench_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workspace_id=workbench_creation_request.workspace_project_id,
                workbench_id=workbench_id,
            )
            session.add(workbench_activity)

            workflows.create_jupyter_workbench(
                build=build,
                user_email=workbench_creation_request.user_email,
                workspace_project_id=workbench_creation_request.workspace_project_id,
                instance_zone=zone,
                instance_name=workbench_id,
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
                id=uuid.uuid4(),
                workspace_id=workspace_creation_request.workspace_project_id,
                invoker_email=workspace_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                build_type=enums.BuildType.WORKSPACE_CREATION,
            )
            session.add(workbench_activity)

            workflows.create_workspace(
                build=build,
                user_email=workspace_creation_request.user_email,
                workbench_activity_id=workbench_activity.id,
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
                id=uuid.uuid4(),
                invoker_email=workspace_deletion_request.user_email,
                workspace_id=workspace_deletion_request.workspace_project_id,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                build_type=enums.BuildType.WORKSPACE_DELETION,
            )
            session.add(workbench_activity)

            workflows.destroy_workspace(
                build=build,
                user_email=workspace_deletion_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def stop_compute_engine_workbench(
    workbench_stop_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_stop_request.workspace_project_id,
        instance_name=workbench_stop_request.workbench_resource_id,
        user_email=workbench_stop_request.user_email,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_stop_request.workspace_project_id,
                invoker_email=workbench_stop_request.user_email,
                build_type=enums.BuildType.WORKBENCH_STOP,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.stop_compute_engine_workbench(
                workspace_project_id=workbench_stop_request.workspace_project_id,
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def start_jupyter_workbench(
    workbench_start_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_start_request.workspace_project_id,
        instance_name=workbench_start_request.workbench_resource_id,
        user_email=workbench_start_request.user_email,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_start_request.workspace_project_id,
                invoker_email=workbench_start_request.user_email,
                build_type=enums.BuildType.WORKBENCH_START,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.start_jupyter_workbench(
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workspace_project_id=workbench_start_request.workspace_project_id,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def update_jupyter_workbench(
    workbench_update_request: entities.WorkbenchUpdate,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_update_request.workspace_project_id,
        instance_name=workbench_update_request.workbench_resource_id,
        user_email=workbench_update_request.user_email,
    )
    build = builds.update_jupyter_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        instance_name=workbench.id,
        machine_type=workbench_update_request.machine_type,
        user_email=workbench_update_request.user_email,
        region=workbench.region,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        service_account_name=workbench.service_account_name,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_update_request.workspace_project_id,
                invoker_email=workbench_update_request.user_email,
                build_type=enums.BuildType.WORKBENCH_UPDATE,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.update_jupyter_workbench(
                build=build,
                workspace_project_id=workbench_update_request.workspace_project_id,
                instance_zone=workbench.zone,
                instance_name=workbench.id,
                user_email=workbench_update_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def destroy_jupyter_workbench(
    workbench_destroy_request: entities.WorkbenchDestroy,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_destroy_request.workspace_project_id,
        instance_name=workbench_destroy_request.workbench_resource_id,
        user_email=workbench_destroy_request.user_email,
    )
    build = builds.destroy_jupyter_workbench_build(
        workspace_project_id=workbench_destroy_request.workspace_project_id,
        instance_name=workbench.id,
        user_email=workbench_destroy_request.user_email,
        region=workbench.region,
        machine_type=workbench.machine_type,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        service_account_name=workbench.service_account_name,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_destroy_request.workspace_project_id,
                invoker_email=workbench_destroy_request.user_email,
                build_type=enums.BuildType.WORKBENCH_DESTROY,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.destroy_jupyter_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                user_email=workbench_destroy_request.user_email,
            )()

            return workbench_activity.id


def create_rstudio_workbench(
    workbench_creation_request: entities.WorkbenchCreate,
) -> uuid.UUID:
    zone, *fallback_zones = services.get_available_zones(
        workbench_creation_request.region
    )
    dataset_identifier = workbench_creation_request.dataset_identifier
    workbench_id = f"rstudio-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    service_account_name = f"rstudio-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"

    build = builds.create_rstudio_workbench_build(
        workspace_project_id=workbench_creation_request.workspace_project_id,
        workspace_numeric_id=workbench_creation_request.workspace_numeric_id,
        region=workbench_creation_request.region,
        zone=zone,
        machine_type=workbench_creation_request.machine_type,
        disk_size=workbench_creation_request.disk_size,
        instance_name=workbench_id,
        service_account_name=service_account_name,
        gpu_accelerator_type=workbench_creation_request.gpu_accelerator_type,
        dataset_identifier=workbench_creation_request.dataset_identifier,
        user_email=workbench_creation_request.user_email,
        bucket_name=workbench_creation_request.bucket_name,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench_id,
                workspace_id=workbench_creation_request.workspace_project_id,
                invoker_email=workbench_creation_request.user_email,
                build_type=enums.BuildType.WORKBENCH_CREATION,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.create_rstudio_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                workspace_project_id=workbench_creation_request.workspace_project_id,
                instance_zone=zone,
                instance_name=workbench_id,
                user_email=workbench_creation_request.user_email,
                fallback_zones=fallback_zones,
            )()

            return workbench_activity.id


def start_rstudio_workbench(
    workbench_start_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_start_request.workspace_project_id,
        instance_name=workbench_start_request.workbench_resource_id,
        user_email=workbench_start_request.user_email,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_start_request.workspace_project_id,
                invoker_email=workbench_start_request.user_email,
                build_type=enums.BuildType.WORKBENCH_START,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.start_rstudio_workbench(
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workspace_project_id=workbench_start_request.workspace_project_id,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def update_rstudio_workbench(
    workbench_update_request: entities.WorkbenchUpdate,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        workbench_update_request.workspace_project_id,
        workbench_update_request.workbench_resource_id,
        workbench_update_request.user_email,
    )

    build = builds.update_rstudio_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        instance_name=workbench.id,
        machine_type=workbench_update_request.machine_type,
        user_email=workbench_update_request.user_email,
        region=workbench.region,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        brand_name=workbench.brand_name,
        service_account_name=workbench.service_account_name,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_update_request.workspace_project_id,
                invoker_email=workbench_update_request.user_email,
                build_type=enums.BuildType.WORKBENCH_UPDATE,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.update_rstudio_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                user_email=workbench_update_request.user_email,
            )()

            return workbench_activity.id


def destroy_rstudio_workbench(
    workbench_destroy_request: entities.WorkbenchDestroy,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        workbench_destroy_request.workspace_project_id,
        workbench_destroy_request.workbench_resource_id,
        workbench_destroy_request.user_email,
    )

    build = builds.destroy_rstudio_workbench_build(
        workspace_project_id=workbench_destroy_request.workspace_project_id,
        instance_name=workbench.id,
        machine_type=workbench.machine_type,
        user_email=workbench_destroy_request.user_email,
        region=workbench.region,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        brand_name=workbench.brand_name,
        service_account_name=workbench.service_account_name,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_destroy_request.workspace_project_id,
                invoker_email=workbench_destroy_request.user_email,
                build_type=enums.BuildType.WORKBENCH_DESTROY,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.destroy_rstudio_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                user_email=workbench_destroy_request.user_email,
            )()

            return workbench_activity.id
