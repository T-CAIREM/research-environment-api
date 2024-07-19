import csv
import os
from datetime import datetime
from os import environ

from typing import List, Optional, Tuple, TypeVar
import requests

from celery import Task, shared_task
from flask_socketio import SocketIO
from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

from research_environment_api.background import (
    build_templates,
    builds,
    constants,
    operations,
    workflows,
    enums,
)
from research_environment_api.background.enums import OperationStatus
from research_environment_api.modules.helpers.exports import helpers as exports_helpers
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.entities import WorkbenchType
from research_environment_api.modules.monitoring_management import models, services

T = TypeVar("T")


class WorkflowTask(Task):
    autoretry_for = (Exception,)
    max_retries = 10
    retry_backoff = True

    def skip_to_last_step(self):
        # The first element of the list is the last task in the chain.
        self.request.chain = self.request.chain[:1]

    def kill_chain(self):
        # Kills the existing chain without any cleanup.
        self.request.chain = None


@shared_task
def start_cloud_build(
    build: CloudBuild,
) -> Tuple[operations.BuildOperation, Tuple[operations.BuildOperation, str]]:
    build_operation = app.config.google_cloud_build_client.create_build(
        build=build, project_id=app.config.project_id
    )
    cloud_build_id = build_operation.metadata.build.id

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

    return operation, operation


@shared_task
def stop_vertex_ai_instance(
    workspace_project_id: str,
    workbench_resource_id: str,
    instance_zone: str,
) -> Tuple[operations.VertexAIOperation, operations.VertexAIOperation]:
    notebooks_client = app.config.google_cloud_notebooks_client
    notebook_instance_path_string = f"projects/{workspace_project_id}/locations/{instance_zone}/instances/{workbench_resource_id}"
    stop_operation = notebooks_client.stop_instance(
        {"name": notebook_instance_path_string},
    )
    operation = operations.VertexAIOperation(name=stop_operation.operation.name)

    return operation, operation


@shared_task
def start_compute_instance(
    workspace_project_id: str,
    instance_name: str,
    instance_zone: str,
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

    return operation, operation


@shared_task
def start_vertex_ai_instance(
    workspace_project_id: str,
    instance_name: str,
    instance_zone: str,
) -> Tuple[operations.VertexAIOperation, operations.VertexAIOperation]:
    notebooks_client = app.config.google_cloud_notebooks_client
    notebook_instance_path_string = f"projects/{workspace_project_id}/locations/{instance_zone}/instances/{instance_name}"
    start_operation = notebooks_client.start_instance(
        {"name": notebook_instance_path_string},
    )
    operation = operations.VertexAIOperation(name=start_operation.operation.name)

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
                .filter_by(workbench_id=workbench_activity.workbench_id)
                .one_or_none()
            )

            if workbench_monitoring_data is None:
                return operation

            workbench_monitoring_data.deleted_at = datetime.now()

    return operation


@shared_task
def export_active_users_per_dataset():
    active_users_per_dataset = services.get_active_users_per_dataset()
    csv_rows = [[entry.dataset_identifier, email] for entry in active_users_per_dataset for email in entry.user_emails]

    filename = f'active_users_per_dataset_{datetime.now().strftime("%Y_%m_%d")}.csv'

    column_names = ['Dataset Identifier', 'User Email']

    exports_helpers.create_csv(csv_rows, filename, column_names)

    exports_helpers.upload_to_gcs(filename, "active_users_per_dataset")

    os.remove(filename)


@shared_task
def export_datasets_total_usage_time():
    workbench_monitoring_entries = services.list_workbench_monitoring_data_entries()
    csv_rows = [[entry.dataset_identifier, entry.user_email, entry.instance_type, entry.total_time] for entry in workbench_monitoring_entries]

    filename = f'datasets_total_usage_time_{datetime.now().strftime("%Y_%m_%d")}.csv'

    column_names = ['Dataset Identifier', 'User Email', 'Instance Type', 'Total Usage Time']

    exports_helpers.create_csv(csv_rows, filename, column_names)

    exports_helpers.upload_to_gcs(filename, "datasets_total_usage_time")

    os.remove(filename)


def _emit_websocket_event(event_name: str, data: dict, room: str) -> None:
    # we need local socketio instance for celery to avoid
    # `NoneType` is not callable error
    socketio = SocketIO(message_queue=environ.get("CELERY_BROKER_URL"), logger=True)
    socketio.emit(
        event_name,
        data,
        room=room,
    )
