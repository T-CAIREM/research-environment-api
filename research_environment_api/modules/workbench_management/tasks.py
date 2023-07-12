from celery import chain, shared_task
from google.cloud.devtools.cloudbuild_v1 import Build

from research_environment_api.modules.config import config
from research_environment_api.modules.db import make_session
from research_environment_api.modules.workbench_management import (
    constants,
    enums,
    models,
)


@shared_task(bind=True)
def check_cloud_build_status(self, build_id: str):
    cloud_build_client = config.google_cloud_build_client
    build_information = cloud_build_client.get_cloud_build_information(
        project_id=config.project_id, build_id=build_id
    )
    status = build_information.status
    if status in [Build.Status.WORKING, Build.Status.QUEUED, Build.Status.PENDING]:
        raise self.retry(max_retries=None, countdown=15)
    return build_information, status


@shared_task
def start_cloud_build(build, build_type):
    build_client = config.google_cloud_build_client
    operation = build_client.create_cloud_build(
        build=build, project_id=config.project_id
    )
    build_id = operation.metadata.build.id
    workbench_activity = models.WorkbenchActivity(
        gcp_build_identifier=build_id, build_type=build_type
    )
    session = make_session()
    session.add(workbench_activity)
    session.commit()
    return build_id


@shared_task
def handle_jupyter_workbench_build_error(
    build_information, status: Build.Status, available_zones: list, build: Build
):
    session = make_session()
    workbench_activity = session.get(models.WorkbenchActivity, build_information.id)
    workbench_activity.build_status = status
    workbench_activity.build_error_information = constants.CLOUD_BUILD_ERROR_MESSAGE[
        build_information.steps[-1].exit_code
    ]
    if status not in [Build.Status.SUCCESS, Build.Status.CANCELLED]:
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
