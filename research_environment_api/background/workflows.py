from typing import List

from celery import chain
from google.cloud.devtools import cloudbuild_v1

from research_environment_api.background import enums, tasks


def create_jupyter_notebook(
    build: cloudbuild_v1.Build, user_email: str, fallback_zones: List[str]
):
    return chain(
        tasks.start_cloud_build.s(
            build=build,
            build_type=enums.BuildType.JUPYTER_CREATION,
            user_email=user_email,
        ),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(
            fallback_zones=fallback_zones, user_email=user_email
        ),
    )


def stop_jupyter_workbench(
    workspace_project_id: str,
    workbench_resource_id: str,
    instance_zone: str,
    user_email: str,
):
    return chain(
        tasks.stop_compute_instance.s(
            workspace_project_id=workspace_project_id,
            workbench_resource_id=workbench_resource_id,
            user_email=user_email,
            instance_zone=instance_zone,
            build_type=enums.BuildType.JUPYTER_STOP,
        ),
        tasks.check_operation_status.s(),
        tasks.process_compute_instance_status.s(),
    )


def start_jupyter_workbench(
    workspace_project_id: str,
    workbench_resource_id: str,
    instance_zone: str,
    user_email: str,
):
    return chain(
        tasks.start_compute_instance.s(
            workspace_project_id=workspace_project_id,
            workbench_resource_id=workbench_resource_id,
            user_email=user_email,
            instance_zone=instance_zone,
            build_type=enums.BuildType.JUPYTER_STOP,
        ),
        tasks.check_operation_status.s(),
        tasks.process_compute_instance_status.s(),
    )


def update_jupyter_workbench(build: cloudbuild_v1.Build, user_email: str):
    return chain(
        tasks.start_cloud_build.s(
            build=build,
            build_type=enums.BuildType.JUPYTER_UPDATE,
            user_email=user_email,
        ),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(user_email=user_email),
    )


def destroy_jupyter_notebook(build: cloudbuild_v1.Build, user_email: str):
    return chain(
        tasks.start_cloud_build.s(
            build=build,
            build_type=enums.BuildType.JUPYTER_DESTROY,
            user_email=user_email,
        ),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(user_email=user_email),
    )


def create_workspace(
    build: cloudbuild_v1.Build,
    user_email: str,
):
    return chain(
        tasks.start_cloud_build.s(
            build=build,
            build_type=enums.BuildType.WORKSPACE_CREATION,
            user_email=user_email,
        ),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(user_email=user_email),
    )


def destroy_workspace(
    build: cloudbuild_v1.Build,
    user_email: str,
):
    return chain(
        tasks.start_cloud_build.s(
            build=build,
            build_type=enums.BuildType.WORKSPACE_DELETION,
            user_email=user_email,
        ),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(user_email=user_email),
    )
