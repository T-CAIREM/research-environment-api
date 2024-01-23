from typing import List, Optional, Tuple, TypeVar
import requests

from celery import Task, shared_task
from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

from research_environment_api.background import (
    build_templates,
    builds,
    constants,
    operations,
    workflows,
)
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.entities import WorkbenchType
from research_environment_api.modules.monitoring_management import models

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
