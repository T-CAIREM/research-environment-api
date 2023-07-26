import random

from research_environment_api.background import builds, constants, workflows
from research_environment_api.modules.workbench_management import entities, services


def create_jupyter_notebook(
    workbench_creation_request: entities.WorkbenchUpdateCreate,
):
    zones = constants.AVAILABLE_ZONES[workbench_creation_request.region]
    zone, *fallback_zones = random.sample(zones, len(zones))

    build = builds.create_jupyter_workbench_build(
        zone=zone, **workbench_creation_request
    )
    return workflows.create_jupyter_notebook(
        build=build,
        user_email=workbench_creation_request.user_email,
        fallback_zones=fallback_zones,
    )()


def stop_jupyter_workbench(workbench_stop_request: entities.WorkbenchStop):
    return workflows.stop_jupyter_workbench(
        workspace_project_id=workbench_stop_request.workspace_project_id,
        workbench_resource_id=workbench_stop_request.workbench_resource_id,
        instance_zone=workbench_stop_request.instance_zone,
        user_email=workbench_stop_request.user_email,
    )()


def update_jupyter_workbench(workbench_update_request: entities.WorkbenchUpdateCreate):
    gce_instance = services.get_jupyter_workbench(
        workbench_resource_id=workbench_update_request.workbench_resource_id,
        gcp_project_id=workbench_update_request.workspace_project_id,
    )
    build = builds.update_jupyter_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        region=workbench_update_request.region,
        machine_type=workbench_update_request.machine_type,
        persistent_disk=workbench_update_request.persistent_disk,
        gpu_accelerator_type=workbench_update_request.gpu_accelerator_type,
        dataset_identifier=workbench_update_request.dataset_identifier,
        user_email=workbench_update_request.user_email,
        bucket_name=workbench_update_request.bucket_name,
        vm_image=workbench_update_request.vm_image,
        jupyter_startup_script_bucket=workbench_update_request.jupyter_startup_script_bucket,
        workbench_resource_id=workbench_update_request.workbench_resource_id,
        zone=gce_instance.zone,
    )
    return workflows.update_jupyter_workbench(
        build=build, user_email=workbench_update_request.user_email
    )()
