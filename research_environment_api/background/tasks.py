import csv
import logging
import os
from datetime import datetime
from os import environ

from typing import List, Optional, Tuple, TypeVar

import google.cloud.resourcemanager_v3
import requests

from celery import Task, shared_task
from flask_socketio import SocketIO
from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild, Build

from research_environment_api.background import (
    build_templates,
    builds,
    constants,
    operations,
    workflows,
    enums,
)

import research_environment_api.modules.workbench_management.services as workbench_services
from research_environment_api.background.enums import OperationStatus
from research_environment_api.modules.helpers.exports import helpers as exports_helpers
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.entities import (
    WorkbenchCollaboratorModification,
)
from research_environment_api.modules.workbench_management.entities import (
    WorkbenchType,
    WorkbenchStatus,
)
from research_environment_api.modules.monitoring_management import models, services


T = TypeVar("T")


class WorkflowTask(Task):
    autoretry_for = (Exception,)
    max_retries = 10
    retry_backoff = True

    def skip_to_last_step(self):
        # The first element of the list is the last task in the chain.
        self.request.chain = self.request.chain[:2]

    def kill_chain(self):
        # Kills the existing chain without any cleanup.
        self.request.chain = None


@shared_task
def start_cloud_build(
    build: CloudBuild,
    workbench_activity_id: str,
) -> Tuple[operations.BuildOperation, Tuple[operations.BuildOperation, str]]:
    build_operation = app.config.google_cloud_build_client.create_build(
        build=build, project_id=app.config.project_id
    )
    cloud_build_id = build_operation.metadata.build.id
    check_and_process_cloud_build_operation.apply_async(
        args=[cloud_build_id, workbench_activity_id], countdown=60 * 30
    )

    operation = operations.BuildOperation(name=build_operation.operation.name)
    return operation, (operation, cloud_build_id)


@shared_task(bind=True)
def process_cloud_build_result(
    self,
    operation_context: Tuple[operations.BuildOperation, str],
    user_email: str,
    workbench_activity_id: str,
    fallback_zones: Optional[List[str]] = None,
    dataset_identifier: str = None,
    collaborators: Optional[List[str]] = None,
) -> Optional[operations.BuildOperation]:
    operation, build_id = operation_context
    build = app.config.google_cloud_build_client.get_build(
        project_id=app.config.project_id, id=build_id
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = (
                session.query(models.WorkbenchActivity)
                .filter_by(id=workbench_activity_id)
                .one()
            )

            if not build.status == CloudBuild.Status.FAILURE:
                return operation

            last_step_exit_code = build.steps[-1].exit_code
            recoverable_error = constants.CLOUD_BUILD_ERROR_MESSAGE.get(
                last_step_exit_code
            )
            is_recoverable = fallback_zones and recoverable_error
            if not is_recoverable:
                workbench_activity.build_error_information = (
                    recoverable_error
                    or "The resource could not be provisioned. Please try again later."
                )
                self.skip_to_last_step()
                return operation

            # Retry the workflow in the next fallback region.
            new_zone, *new_fallback_zones = fallback_zones
            build.substitutions["_ZONE"] = new_zone
            if build.substitutions["_WORKBENCH_TYPE"] == WorkbenchType.JUPYTER:
                build.steps = build_templates.CREATE_JUPYTER_WORKBENCH_STEPS
                workflows.create_jupyter_workbench(
                    build=build,
                    workspace_project_id=build.substitutions["_PROJECT_ID"],
                    instance_zone=new_zone,
                    instance_name=build.substitutions["_INSTANCE_NAME"],
                    fallback_zones=new_fallback_zones,
                    user_email=user_email,
                    workbench_activity_id=workbench_activity_id,
                    dataset_identifier=dataset_identifier,
                )()
                self.kill_chain()
            elif build.substitutions["_WORKBENCH_TYPE"] == WorkbenchType.COLLABORATIVE:
                build.steps = build_templates.CREATE_COLLABORATIVE_WORKBENCH_STEPS
                workflows.create_collaborative_workbench(
                    build=build,
                    workspace_project_id=build.substitutions["_PROJECT_ID"],
                    instance_zone=new_zone,
                    instance_name=build.substitutions["_INSTANCE_NAME"],
                    fallback_zones=new_fallback_zones,
                    user_email=user_email,
                    workbench_activity_id=workbench_activity_id,
                    dataset_identifier=dataset_identifier,
                    collaborators=collaborators,
                )()
                self.kill_chain()
            else:
                build.steps = build_templates.CREATE_RSTUDIO_WORKBENCH_STEPS
                workflows.create_rstudio_workbench(
                    build=build,
                    workspace_project_id=build.substitutions["_PROJECT_ID"],
                    instance_zone=new_zone,
                    instance_name=build.substitutions["_INSTANCE_NAME"],
                    fallback_zones=new_fallback_zones,
                    user_email=user_email,
                    workbench_activity_id=workbench_activity_id,
                    dataset_identifier=dataset_identifier,
                )()
                self.kill_chain()


@shared_task
def set_workflow_status(operation: operations.Operation, workbench_activity_id: str):
    with app.database_session() as session:
        with session.begin():
            workbench_activity = (
                session.query(models.WorkbenchActivity)
                .filter_by(id=workbench_activity_id)
                .one()
            )
            workbench_activity.build_status = operation.status()
    workbench_activity_str = str(workbench_activity_id)
    _emit_websocket_event(
        "workflow_update",
        {"workbench_activity_id": workbench_activity_str},
        workbench_activity_str,
    )
    return operation


@shared_task
def stop_compute_instance(
    workspace_project_id: str,
    workbench_resource_id: str,
    instance_zone: str,
    workbench_activity_id: str,
) -> Tuple[operations.InstanceOperation, operations.InstanceOperation]:
    instance_client = app.config.google_compute_engine_instances_client
    stop_operation = instance_client.stop(
        project=workspace_project_id,
        instance=workbench_resource_id,
        zone=instance_zone,
    )

    operation = operations.InstanceOperation(
        project_id=workspace_project_id, zone=instance_zone, name=stop_operation.name
    )
    check_and_process_cloud_build_operation.apply_async(
        args=[None, workbench_activity_id], countdown=60 * 30
    )

    return operation, operation


@shared_task
def stop_vertex_ai_instance(
    workspace_project_id: str,
    workbench_resource_id: str,
    instance_zone: str,
    workbench_activity_id: str,
) -> Tuple[operations.VertexAIOperation, operations.VertexAIOperation]:
    notebooks_client = app.config.google_cloud_notebooks_client
    notebook_instance_path_string = f"projects/{workspace_project_id}/locations/{instance_zone}/instances/{workbench_resource_id}"
    stop_operation = notebooks_client.stop_instance(
        {"name": notebook_instance_path_string},
    )
    operation = operations.VertexAIOperation(name=stop_operation.operation.name)
    check_and_process_cloud_build_operation.apply_async(
        args=[None, workbench_activity_id], countdown=60 * 30
    )

    return operation, operation


@shared_task
def start_compute_instance(
    workspace_project_id: str,
    instance_name: str,
    instance_zone: str,
    workbench_activity_id: str,
) -> Tuple[operations.InstanceOperation, operations.InstanceOperation]:
    instance_client = app.config.google_compute_engine_instances_client
    start_operation = instance_client.start(
        project=workspace_project_id,
        instance=instance_name,
        zone=instance_zone,
    )

    operation = operations.InstanceOperation(
        project_id=workspace_project_id, zone=instance_zone, name=start_operation.name
    )
    check_and_process_cloud_build_operation.apply_async(
        args=[None, workbench_activity_id], countdown=60 * 30
    )

    return operation, operation


@shared_task
def start_vertex_ai_instance(
    workspace_project_id: str,
    instance_name: str,
    instance_zone: str,
    workbench_activity_id: str,
) -> Tuple[operations.VertexAIOperation, operations.VertexAIOperation]:
    notebooks_client = app.config.google_cloud_notebooks_client
    notebook_instance_path_string = f"projects/{workspace_project_id}/locations/{instance_zone}/instances/{instance_name}"
    start_operation = notebooks_client.start_instance(
        {"name": notebook_instance_path_string},
    )
    operation = operations.VertexAIOperation(name=start_operation.operation.name)

    check_and_process_cloud_build_operation.apply_async(
        args=[None, workbench_activity_id], countdown=60 * 30
    )

    return operation, operation


@shared_task(bind=True, max_retries=None, countdown=30)
def check_vertex_ai_setup_status(
    self,
    passthrough: T,
    workspace_project_id: str,
    instance_zone: str,
    instance_name: str,
) -> T:
    instance_client = app.config.google_compute_engine_instances_client
    instance = instance_client.get(
        project=workspace_project_id,
        zone=instance_zone,
        instance=instance_name,
    )

    metadata = {item.key: item.value for item in instance.metadata.items}
    if "proxy-url" not in metadata:
        self.retry(countdown=30)

    return passthrough


@shared_task(bind=True, max_retries=None, countdown=30)
def check_operation_status(
    self,
    operation_context: Tuple[operations.Operation, T],
) -> T:
    operation, passthrough = operation_context
    if not operation.is_done():
        raise self.retry(countdown=30)

    return passthrough


@shared_task(bind=True, max_retries=None, countdown=30)
def check_rstudio_page_status(
    self,
    passthrough: T,
    workspace_project_id: str,
    instance_zone: str,
    instance_name: str,
):
    instance_client = app.config.google_compute_engine_instances_client
    instance = instance_client.get(
        project=workspace_project_id,
        zone=instance_zone,
        instance=instance_name,
    )

    metadata = {item.key: item.value for item in instance.metadata.items}
    try:
        requests.get(f"https://{metadata['proxy-url']}", timeout=5)
    except requests.exceptions.SSLError:
        self.retry(countdown=30)

    return passthrough


@shared_task
def add_monitoring_entry(
    operation: operations.Operation,
    workbench_activity_id: str,
    instance_type: enums.InstanceType,
    dataset_identifier: str,
):
    # locally workbenches fail even if they are created, to test this feature please comment below condition
    # and change skip_to_last_step function to skip to second to last step
    if operation.status() == OperationStatus.FAILURE:
        return operation

    with app.database_session() as session:
        with session.begin():
            workbench_activity = (
                session.query(models.WorkbenchActivity)
                .filter_by(id=workbench_activity_id)
                .one()
            )

            workbench_monitoring_data = models.WorkbenchMonitoringData(
                workbench_id=workbench_activity.workbench_id,
                user_email=workbench_activity.invoker_email,
                dataset_identifier=dataset_identifier,
                instance_type=instance_type,
                created_at=datetime.now(),
            )

            session.add(workbench_monitoring_data)
            session.commit()

    return operation


@shared_task
def mark_monitoring_entry_as_deleted(
    operation: operations.Operation, workbench_activity_id: str
):
    if operation.status() == OperationStatus.FAILURE:
        return operation

    with app.database_session() as session:
        with session.begin():
            workbench_activity = (
                session.query(models.WorkbenchActivity)
                .filter_by(id=workbench_activity_id)
                .one()
            )

            workbench_monitoring_data = (
                session.query(models.WorkbenchMonitoringData)
                .filter(
                    models.WorkbenchMonitoringData.workbench_id
                    == workbench_activity.workbench_id,
                    models.WorkbenchMonitoringData.deleted_at.is_(None),
                )
                .all()
            )

            if not workbench_monitoring_data:
                return operation

            for record in workbench_monitoring_data:
                record.deleted_at = datetime.now()

            session.commit()

    return operation


@shared_task
def export_active_users_per_dataset():
    active_users_per_dataset = services.get_active_users_per_dataset()
    csv_rows = [
        [entry.dataset_identifier, email]
        for entry in active_users_per_dataset
        for email in entry.user_emails
    ]

    filename = f'active_users_per_dataset_{datetime.now().strftime("%Y_%m_%d")}.csv'

    column_names = ["Dataset Identifier", "User Email"]

    exports_helpers.create_csv(csv_rows, filename, column_names)

    exports_helpers.upload_to_gcs(filename, "active_users_per_dataset")

    os.remove(filename)


@shared_task
def export_datasets_total_usage_time():
    workbench_monitoring_entries = services.list_workbench_monitoring_data_entries()
    csv_rows = [
        [
            entry.dataset_identifier,
            entry.user_email,
            entry.instance_type,
            entry.total_time,
        ]
        for entry in workbench_monitoring_entries
    ]

    filename = f'datasets_total_usage_time_{datetime.now().strftime("%Y_%m_%d")}.csv'

    column_names = [
        "Dataset Identifier",
        "User Email",
        "Instance Type",
        "Total Usage Time",
    ]

    exports_helpers.create_csv(csv_rows, filename, column_names)

    exports_helpers.upload_to_gcs(filename, "datasets_total_usage_time")

    os.remove(filename)


@shared_task
def mark_monitoring_entry_for_stale_workbenches():
    with app.database_session() as session:
        with session.begin():
            all_active_workbenches = (
                session.query(
                    models.WorkbenchMonitoringData,
                    models.WorkbenchActivity.workspace_id,
                )
                .join(
                    models.WorkbenchActivity,
                    models.WorkbenchMonitoringData.workbench_id
                    == models.WorkbenchActivity.workbench_id,
                    isouter=True,
                )
                .filter(models.WorkbenchMonitoringData.deleted_at.is_(None))
                .all()
            )

            for monitoring_data, workspace_id in all_active_workbenches:
                workbench = workbench_services.get_compute_engine_workbench(
                    gcp_project_id=workspace_id,
                    instance_name=monitoring_data.workbench_id,
                    user_email=monitoring_data.user_email,
                )
                if workbench.status == WorkbenchStatus.STOPPED:
                    monitoring_data.deleted_at = datetime.now()

            session.commit()


@shared_task(bind=True)
def check_and_process_cloud_build_operation(self, build_id, workbench_activity_id):
    logging.info(
        f"Running check_and_process_cloud_build_operation for {workbench_activity_id}."
    )

    build = None
    # for start/stop operation there is not build to check
    if build_id:
        build = app.config.google_cloud_build_client.get_build(
            project_id=app.config.project_id, id=build_id
        )

        if _build_in_progress(build):
            logging.info(f"Build {build_id} is still in progress.")
            self.retry(countdown=60 * 30)
            return

    with app.database_session() as session:
        with session.begin():
            workbench_activity = (
                session.query(models.WorkbenchActivity)
                .filter_by(id=workbench_activity_id)
                .one()
            )

            if not workbench_activity.build_status == enums.WorkflowStatus.IN_PROGRESS:
                logging.info(
                    f"Build {workbench_activity_id} already processed properly."
                )
                return

            if build and build.status == Build.Status.SUCCESS:
                workbench_activity.build_status = enums.WorkflowStatus.SUCCESS
                logging.info(f"Workbench {workbench_activity_id} processed correctly.")
                session.commit()
                return

            type = workbench_activity.build_type.split("_")[0]

            if type == "workspace" or type == "shared":
                project = app.config.google_cloud_resource_client.get_project(
                    name=f"projects/{workbench_activity.workspace_id}"
                )

                workbench_activity.build_status = _get_activity_status(
                    workbench_activity, project
                )
            else:
                try:
                    instance = _fetch_gce_instance(
                        workbench_activity.workspace_id, workbench_activity.workbench_id
                    )
                    if (
                        instance.status != "PROVISIONING"
                        and instance.status != "STAGING"
                    ):
                        workbench_activity.build_status = _get_activity_status(
                            workbench_activity, instance
                        )
                    else:
                        logging.info(
                            f"Workbench {workbench_activity_id} is still being provisioned."
                        )
                        self.retry(countdown=60 * 30)
                        return
                except IndexError:
                    # instance is not existing
                    workbench_activity.build_status = _get_activity_status(
                        workbench_activity, None
                    )

            logging.info(f"Workbench {workbench_activity_id} processed correctly.")
            session.commit()

    return


@shared_task
def assign_initial_collaborators(
    operation: operations.Operation,
    collaborators: list,
    instance_name: str,
    workspace_project_id: str,
    user_email: str,
):

    # locally workbenches fail even if they are created, to test this feature please comment below condition
    if operation.status() == OperationStatus.FAILURE:
        logging.warning(
            f"Skipping collaborator assignment for {instance_name} due to previous operation failure"
        )
        return operation

    try:
        service_account_name = workbench_services.get_compute_engine_workbench(
            gcp_project_id=workspace_project_id,
            instance_name=instance_name,
            user_email=user_email,
        ).service_account_name

        collaborators_entity = WorkbenchCollaboratorModification(
            service_account_name=service_account_name,
            workspace_project_id=workspace_project_id,
            collaborators=collaborators,
        )
        workbench_services.add_collaborators_to_workbench(collaborators_entity)
        logging.info(
            f"Successfully assigned collaborators for workbench {instance_name}"
        )
    except Exception as e:
        logging.error(
            f"Failed to assign collaborators for workbench {instance_name}: {str(e)}"
        )

    return operation


def _get_activity_status(workbench_activity: models.WorkbenchActivity, instance):
    if workbench_activity.build_type in [
        enums.BuildType.WORKSPACE_DELETION,
        enums.BuildType.SHARED_WORKSPACE_DELETION,
    ]:
        if not instance:
            return enums.WorkflowStatus.SUCCESS

        return (
            enums.WorkflowStatus.SUCCESS
            if instance.status
            == google.cloud.resourcemanager_v3.Project.State.DELETE_REQUESTED
            else enums.WorkflowStatus.FAILURE
        )

    if workbench_activity.build_type in [
        enums.BuildType.WORKSPACE_CREATION,
        enums.BuildType.SHARED_WORKSPACE_CREATION,
    ]:
        if not instance:
            return enums.WorkflowStatus.FAILURE

        return (
            enums.WorkflowStatus.SUCCESS
            if instance.status == google.cloud.resourcemanager_v3.Project.State.ACTIVE
            else enums.WorkflowStatus.FAILURE
        )

    if workbench_activity.build_type == enums.BuildType.WORKBENCH_DESTROY:
        if not instance:
            return enums.WorkflowStatus.SUCCESS

        return (
            enums.WorkflowStatus.SUCCESS
            if instance.status == "TERMINATED"
            else enums.WorkflowStatus.FAILURE
        )

    if workbench_activity.build_type == enums.BuildType.WORKBENCH_STOP:
        if not instance:
            return enums.WorkflowStatus.FAILURE

        return (
            enums.WorkflowStatus.SUCCESS
            if instance.status == "TERMINATED"
            else enums.WorkflowStatus.FAILURE
        )

    if not instance:
        return enums.WorkflowStatus.FAILURE

    return (
        enums.WorkflowStatus.SUCCESS
        if instance.status == "RUNNING"
        else enums.WorkflowStatus.FAILURE
    )


def _build_in_progress(build: Build):
    return build.status in [
        Build.Status.WORKING,
        Build.Status.QUEUED,
        Build.Status.PENDING,
    ]


def _fetch_gce_instance(gcp_project_id: str, workbench_id):
    gce_instances_per_zone = (
        app.config.google_compute_engine_instances_client.aggregated_list(
            project=gcp_project_id
        )
    )

    return [
        instance
        for zone, instances_in_region in gce_instances_per_zone
        for instance in instances_in_region.instances
        if instance.name == workbench_id
    ][0]


def _emit_websocket_event(event_name: str, data: dict, room: str) -> None:
    # we need local socketio instance for celery to avoid
    # `NoneType` is not callable error
    socketio = SocketIO(message_queue=environ.get("CELERY_BROKER_URL"), logger=True)
    socketio.emit(
        event_name,
        data,
        to=room,
    )
