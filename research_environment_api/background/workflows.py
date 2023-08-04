from typing import List

from celery import chain
from google.cloud.devtools import cloudbuild_v1

from research_environment_api.background import enums, tasks


def create_jupyter_workbench(
    build: cloudbuild_v1.Build,
    user_email: str,
    fallback_zones: List[str],
    workbench_activity_id: str,
):
    return chain(
        tasks.start_cloud_build.s(
            build=build,
        ),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(
            fallback_zones=fallback_zones,
            user_email=user_email,
            workbench_activity_id=workbench_activity_id,
        ),
        tasks.set_workflow_status(workbench_activity_id=workbench_activity_id),
    )


def stop_jupyter_workbench(
    workspace_project_id: str,
    workbench_resource_id: str,
    instance_zone: str,
    workbench_activity_id: str,
):
    return chain(
        tasks.stop_compute_instance.s(
            workspace_project_id=workspace_project_id,
            workbench_resource_id=workbench_resource_id,
            instance_zone=instance_zone,
        ),
        tasks.check_operation_status.s(),
        tasks.process_compute_instance_status.s(),
        tasks.set_workflow_status(workbench_activity_id=workbench_activity_id),
    )


def start_jupyter_workbench(
    workspace_project_id: str,
    workbench_resource_id: str,
    instance_zone: str,
    workbench_activity_id: str,
):
    return chain(
        tasks.start_compute_instance.s(
            workspace_project_id=workspace_project_id,
            workbench_resource_id=workbench_resource_id,
            instance_zone=instance_zone,
        ),
        tasks.check_operation_status.s(),
        tasks.process_compute_instance_status.s(),
        tasks.set_workflow_status(workbench_activity_id=workbench_activity_id),
    )


def update_jupyter_workbench(
    build: cloudbuild_v1.Build, user_email: str, workbench_activity_id: str
):
    return chain(
        tasks.start_cloud_build.s(build=build),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(user_email=user_email),
        tasks.set_workflow_status(workbench_activity_id=workbench_activity_id),
    )


def destroy_jupyter_workbench(build: cloudbuild_v1.Build, user_email: str):
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
    build: cloudbuild_v1.Build, user_email: str, workbench_activity_id: str
):
    return chain(
        tasks.start_cloud_build.s(build=build),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(user_email=user_email),
        tasks.set_workflow_status(workbench_activity_id=workbench_activity_id),
    )


def destroy_workspace(
    build: cloudbuild_v1.Build, user_email: str, workbench_activity_id: str
):
    return chain(
        tasks.start_cloud_build.s(build=build),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(user_email=user_email),
        tasks.set_workflow_status(workbench_activity_id=workbench_activity_id),
    )
