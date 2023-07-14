from celery import chain, shared_task
from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild
from google.cloud.compute import Instance as CloudInstance

from research_environment_api.modules.app import app
from research_environment_api.modules.celery_management import constants, enums
from research_environment_api.modules.workbench_management import models


@shared_task(bind=True)
def check_cloud_build_status(self, build_id: str):
    cloud_build_client = app.config.google_cloud_build_client
    build_information = cloud_build_client.get_build(
        project_id=app.config.project_id, id=build_id
    )
    status = build_information.status
    if status in [
        CloudBuild.Status.WORKING,
        CloudBuild.Status.QUEUED,
        CloudBuild.Status.PENDING,
    ]:
        raise self.retry(max_retries=None, countdown=15)
    return build_information, status


@shared_task
def start_cloud_build(build, build_type):
    build_client = app.config.google_cloud_build_client
    operation = build_client.create_build(build=build, project_id=app.config.project_id)
    build_id = operation.metadata.build.id
    workbench_activity = models.WorkbenchActivity(
        gcp_identifier=build_id, build_type=build_type
    )
    with app.database_session() as session:
        session.add(workbench_activity)
        session.commit()

    return build_id


@shared_task
def handle_jupyter_workbench_build_error(
    build_information_status_tuple: tuple, available_zones: list, build: Build
):
    build_information, status = build_information_status_tuple
    with app.database_session() as session:
        workbench_activity = session.get(models.WorkbenchActivity, build_information.id)
        workbench_activity.build_status = status
        workbench_activity.build_error_information = (
            constants.CLOUD_BUILD_ERROR_MESSAGE[build_information.steps[-1].exit_code]
        )
        if status not in [CloudBuild.Status.SUCCESS, CloudBuild.Status.CANCELLED]:
            if available_zones:
                build.substitutions["_ZONE"] = available_zones.pop(0)
                chain(
                    start_cloud_build.s(
                        build=build, build_type=enums.BuildType.JUPYTER_CREATION_RETRY
                    ),
                    check_cloud_build_status.s(),
                    handle_jupyter_workbench_build_error.s(available_zones, build),
                )
            else:
                workbench_activity.build_error_information = (
                    "No resources in any zone. Try again later"
                )

        session.commit()


@shared_task
def handle_jupyter_workbench_stop_error(instance_operation_identifier_tuple: tuple):
    instance, operation_identifier = instance_operation_identifier_tuple
    session = make_session()
    workbench_activity = session.get(models.WorkbenchActivity, operation_identifier)
    workbench_activity.build_status = instance.status
    session.commit()
    # TODO: handle jupyter stop errors by moving persistant disc and changing zone


@shared_task(bind=True)
def check_compute_instance_status(
    self,
    workbench_zone_gcp_id_tuple: tuple,
    user_project: str,
    instance_name: str,
):
    workbench_zone, gcp_identifier = workbench_zone_gcp_id_tuple
    instance_client = config.google_compute_engine_instances_client
    instance = instance_client.get(
        project=user_project, instance=instance_name, zone=workbench_zone
    )
    if instance.status in [
        CloudInstance.Status.STOPPED,
        CloudInstance.Status.SUSPENDED,
        CloudInstance.Status.TERMINATED,
        CloudInstance.Status.RUNNING,
    ]:
        return self.retry(max_retries=None, countdown=30)
    return instance, gcp_identifier


@shared_task
def stop_compute_instance(
    user_project: str,
    instance_name: str,
    gcp_workbench_identifier: str,
    build_type: enums.BuildType,
):
    session = make_session()
    workbench_zone = session.get(models.WorkbenchMetadata, gcp_workbench_identifier).zone
    instance_client = config.google_compute_engine_instances_client
    operation = instance_client.stop(
        project=user_project, instance=instance_name, zone=workbench_zone
    )
    workbench_activity = models.WorkbenchActivity(
        gcp_identifier=operation.name, build_type=build_type
    )
    session.add(workbench_activity)
    session.commit()
    return (
        workbench_zone,
        workbench_activity.gcp_identifier,
    )
