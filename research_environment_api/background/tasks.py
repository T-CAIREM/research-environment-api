from typing import Any, List, Optional, Tuple

from celery import Task, shared_task
from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

from research_environment_api.background import builds, constants, operations, workflows
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import models, services


class WorkflowTask(Task):
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

            if not fallback_zones:
                # FIXME: Why does this error assume that there were insufficient resources?
                workbench_activity.build_error_information = (
                    "Workflow failed in all available zones. Please try again later."
                )
                # Short-circuit the workflow.
                self.skip_to_last_step()
                return operation

            # Retry the workflow in the next fallback region.
            workbench_activity.build_error_information = (
                constants.CLOUD_BUILD_ERROR_MESSAGE[build.steps[-1].exit_code]
            )
            new_zone, *new_fallback_zones = fallback_zones
            build.substitutions["_ZONE"] = new_zone
            workflows.create_jupyter_workbench(
                build=build,
                fallback_zones=new_fallback_zones,
                user_email=user_email,
                workbench_activity_id=workbench_activity_id,
            )()
            self.kill_chain()


@shared_task(bind=True)
def create_default_service_stopping_build(
    self, _operation: operations.Operation, workspace_project_id: str
) -> CloudBuild:
    versions = services.get_app_engine_service_versions(
        workspace_project_id, services.DEFAULT_APP_ENGINE_SERVICE_ID
    )
    # The default service will only ever have one version.
    default_version = next(iter(versions))
    stop_default_engine_build = builds.stop_rstudio_workbench_build(
        workspace_project_id=workspace_project_id,
        workbench_resource_id=default_version.id,
    )
    return stop_default_engine_build


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
    workbench_resource_id: str,
    instance_zone: str,
) -> Tuple[operations.InstanceOperation, operations.InstanceOperation]:
    instance_client = app.config.google_compute_engine_instances_client
    start_operation = instance_client.start(
        project=workspace_project_id,
        instance=workbench_resource_id,
        zone=instance_zone,
    )

    operation = operations.InstanceOperation(
        project_id=workspace_project_id, zone=instance_zone, name=start_operation.name
    )

    return operation, operation


@shared_task
def process_compute_instance_status(instance_operation_identifier_tuple: tuple):
    # TODO: Figure a sensible way to process this.
    operation, operation_identifier = instance_operation_identifier_tuple
    with app.database_session() as session:
        workbench_activity = (
            session.query(models.WorkbenchActivity)
            .filter_by(gcp_identifier=operation_identifier)
            .one()
        )
        # FIXME: Makes no sense semantically.
        workbench_activity.build_status = operation.status()
        session.commit()


@shared_task(bind=True, max_retries=None, countdown=30)
def check_operation_status(
    self,
    operation_context: Tuple[operations.Operation, Any],
) -> Any:
    operation, passthrough = operation_context
    if not operation.is_done():
        raise self.retry(countdown=30)

    return passthrough
