from typing import Any, List, Tuple

from celery import shared_task
from google.api_core.future import polling
from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

from research_environment_api.background import constants, enums, operations, workflows
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import models


@shared_task
def start_cloud_build(
    build: CloudBuild, build_type: enums.BuildType, user_email: str
) -> Tuple[polling.PollingFuture, CloudBuild]:
    build_operation = app.config.google_cloud_build_client.create_build(
        build=build, project_id=app.config.project_id
    )
    cloud_build_id = build_operation.metadata.build.id

    workbench_activity = models.WorkbenchActivity(
        gcp_identifier=cloud_build_id,
        build_type=build_type,
        invoker_email=user_email,
    )
    with app.database_session() as session:
        session.add(workbench_activity)
        session.commit()

    operation = operations.BuildOperation(name=build_operation.operation.name)
    return operation, cloud_build_id


@shared_task
def process_cloud_build_result(
    build_id: str,
    fallback_zones: List[str],
    user_email: str,
):
    build = app.config.google_cloud_build_client.get_build(
        project_id=app.config.project_id, id=build_id
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = (
                session.query(models.WorkbenchActivity)
                .filter_by(gcp_identifier=build.id)
                .one()
            )
            workbench_activity.build_status = build.status
            if not build.status == CloudBuild.Status.FAILURE:
                return

            if not fallback_zones:
                # Failed in all fallback regions.
                # FIXME: Why does this error assume that there were insufficient resources?
                workbench_activity.build_error_information = (
                    "No resources in any zone. Try again later"
                )
                return

            # Retry the workflow in the next fallback region.
            workbench_activity.build_error_information = (
                constants.CLOUD_BUILD_ERROR_MESSAGE[build.steps[-1].exit_code]
            )
            new_zone, *new_fallback_zones = fallback_zones
            build.substitutions["_ZONE"] = new_zone
            workflows.create_jupyter_notebook(
                build=build,
                fallback_zones=new_fallback_zones,
                user_email=user_email,
            )


@shared_task
def stop_compute_instance(
    workspace_project_id: str,
    workbench_resource_id: str,
    user_email: str,
    build_type: enums.BuildType,
    instance_zone: str,
) -> Tuple[operations.Operation, None]:
    instance_client = app.config.google_compute_engine_instances_client
    stop_operation = instance_client.stop(
        project=workspace_project_id,
        instance=workbench_resource_id,
        zone=instance_zone,
    )

    with app.database_session() as session:
        workbench_activity = models.WorkbenchActivity(
            gcp_identifier=stop_operation.name,
            build_type=build_type,
            invoker_email=user_email,
        )
        session.add(workbench_activity)
        session.commit()

    operation = operations.InstanceOperation(
        project_id=workspace_project_id, zone=instance_zone, name=stop_operation.name
    )

    return operation, None


@shared_task
def start_compute_instance(
    workspace_project_id: str,
    workbench_resource_id: str,
    user_email: str,
    build_type: enums.BuildType,
    instance_zone: str,
):
    with app.database_session() as session:
        instance_client = app.config.google_compute_engine_instances_client
        start_operation = instance_client.start(
            project=workspace_project_id,
            instance=workbench_resource_id,
            zone=instance_zone,
        )
        workbench_activity = models.WorkbenchActivity(
            gcp_identifier=start_operation.name,
            build_type=build_type,
            invoker_email=user_email,
        )
        session.add(workbench_activity)
        session.commit()

    operation = operations.InstanceOperation(
        project_id=workspace_project_id, zone=instance_zone, name=start_operation.name
    )

    return operation, None


@shared_task
def process_compute_instance_status(instance_operation_identifier_tuple: tuple):
    # TODO: Figure a sensible way to process this.
    instance, operation_identifier = instance_operation_identifier_tuple
    with app.database_session() as session:
        workbench_activity = (
            session.query(models.WorkbenchActivity)
            .filter_by(gcp_identifier=operation_identifier)
            .one()
        )
        # FIXME: Makes no sense semantically.
        workbench_activity.build_status = instance.status
        session.commit()


@shared_task(bind=True)
def check_operation_status(
    self,
    operation_context: Tuple[operations.Operation, Any],
) -> Any:
    operation, passthrough = operation_context
    if not operation.done():
        raise self.retry(max_retries=None, countdown=30)

    return passthrough
