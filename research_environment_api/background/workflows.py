from typing import List

from celery import chain
from google.cloud.devtools import cloudbuild_v1

from research_environment_api.background import tasks


def create_jupyter_workbench(
    build: cloudbuild_v1.Build,
    user_email: str,
    workspace_project_id: str,
    instance_zone: str,
    instance_name: str,
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
        tasks.check_vertex_ai_setup_status.s(
            workspace_project_id=workspace_project_id,
            instance_zone=instance_zone,
            instance_name=instance_name,
        ),
        tasks.set_workflow_status.s(workbench_activity_id=workbench_activity_id),
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
        tasks.set_workflow_status.s(workbench_activity_id=workbench_activity_id),
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
        tasks.set_workflow_status.s(workbench_activity_id=workbench_activity_id),
    )


def update_jupyter_workbench(
    build: cloudbuild_v1.Build, user_email: str, workbench_activity_id: str
):
    return chain(
        tasks.start_cloud_build.s(build=build),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(
            workbench_activity_id=workbench_activity_id, user_email=user_email
        ),
        tasks.set_workflow_status.s(workbench_activity_id=workbench_activity_id),
    )


def destroy_jupyter_workbench(
    build: cloudbuild_v1.Build, user_email: str, workbench_activity_id: str
):
    return chain(
        tasks.start_cloud_build.s(build=build),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(
            workbench_activity_id=workbench_activity_id, user_email=user_email
        ),
        tasks.set_workflow_status.s(workbench_activity_id=workbench_activity_id),
    )


def create_workspace(
    build: cloudbuild_v1.Build,
    user_email: str,
    workbench_activity_id: str,
    workspace_project_id: str,
):
    return chain(
        tasks.start_cloud_build.s(build=build),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(
            workbench_activity_id=workbench_activity_id, user_email=user_email
        ),
        tasks.create_default_service_stopping_build.s(
            workspace_project_id=workspace_project_id
        ),
        tasks.start_cloud_build.s(),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(
            workbench_activity_id=workbench_activity_id, user_email=user_email
        ),
        tasks.set_workflow_status.s(workbench_activity_id=workbench_activity_id),
    )


def destroy_workspace(
    build: cloudbuild_v1.Build, user_email: str, workbench_activity_id: str
):
    return chain(
        tasks.start_cloud_build.s(build=build),
        tasks.check_operation_status.s(),
        tasks.process_cloud_build_result.s(
            workbench_activity_id=workbench_activity_id, user_email=user_email
        ),
        tasks.set_workflow_status.s(workbench_activity_id=workbench_activity_id),
    )
