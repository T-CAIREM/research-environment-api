from celery import shared_task
from research_environment_api.modules.config import config
from research_environment_api.modules.db import session
from research_environment_api.modules.workbench_management import (
    exceptions,
    models,
    constants,
)

from google.cloud.devtools.cloudbuild_v1 import Build


@shared_task()
def handle_build_error(build_id: str, status: Build.Status):
    workbench_activity = session.get(models.WorkbenchActivity, build_id)
    workbench_activity.build_status = status
    session.commit()
    if status is not Build.Status.SUCCESS:
        constants.HANDLERS_MAPPING[workbench_activity.build_type]()


@shared_task(
    autoretry_for=(
        exceptions.CloudBuildInProgress,
    ),
    retry_kwargs={"max_retries": None, "countdown": 15},
    link=handle_build_error(),
)  # 6 minutes timeout
def check_cloud_build_status(build_id: str):
    cloud_build_client = config.google_cloud_build_client
    build = cloud_build_client.get_cloud_build_information(
        project_id=config.project_id, build_id=build_id
    )
    status = build.status
    if status in [Build.Status.WORKING, Build.Status.QUEUED, Build.Status.PENDING]:
        raise exceptions.CloudBuildInProgress
    return build_id, status


@shared_task(link=check_cloud_build_status())
def start_cloud_build(build, build_type):
    build_client = config.google_cloud_build_client
    operation = build_client.cloud_build_client(
        build=build, project_id=config.project_id
    )
    build_id = operation.metadata.build.id
    workbench_activity = models.WorkbenchActivity(gcp_build_identifier=build_id, build_type=build_type)
    session.add(workbench_activity)
    session.commit()
    return build_id
