import random
from copy import deepcopy

from celery import chain

from research_environment_api.background import constants, enums, factories, tasks
from research_environment_api.modules.app import app


def create_cloud_build_source():
    return {
        "repo_source": {
            "project_id": app.config.project_id,
            "repo_name": app.config.terraform_repo_name,
            "branch_name": app.config.terraform_branch_name,
        }
    }


def get_available_zones(region: str):
    available_zones = deepcopy(constants.AVAILABLE_ZONES[region])
    random.shuffle(available_zones)
    return available_zones.pop(0), available_zones


def create_jupyter_notebook(workbench_creation_request):
    zone, available_zones = get_available_zones(workbench_creation_request.region)

    vm_image = (
        "common-cu110-notebooks"
        if workbench_creation_request.gpu_accelerator
        else "r-4-2-cpu-experimental-notebooks"
    )

    build = factories.BuildFactory(
        app.config.project_id, create_cloud_build_source()
    ).create_jupyter(
        machine_type=workbench_creation_request.machine_type,
        user_project_id=workbench_creation_request.user_project_id,
        dataset=workbench_creation_request.dataset,
        email_id=workbench_creation_request.email_id,
        bucket_name=workbench_creation_request.bucket_name,
        region=workbench_creation_request.region,
        persistent_disk=workbench_creation_request.persistent_disk,
        gpu_accelerator=workbench_creation_request.gpu_accelerator,
        vm_image=vm_image,
        zone=zone,
        jupyter_startup_script_bucket=workbench_creation_request.jupyter_startup_script_bucket,
    )
    return chain(
        tasks.start_cloud_build.s(
            build=build,
            build_type=enums.BuildType.JUPYTER_CREATION,
            invoker_email=workbench_creation_request.email_id,
        ),
        tasks.check_cloud_build_status.s(),
        tasks.handle_jupyter_workbench_build_error.s(available_zones, build),
    )()


def stop_jupyter_workbench(workbench_stop_request):
    return chain(
        tasks.stop_compute_instance.s(
            user_project=workbench_stop_request.user_project,
            instance_name=workbench_stop_request.instance_name,
            gcp_workbench_identifier=workbench_stop_request.gcp_identifier,
            invoker_email=workbench_stop_request.invoker_email,
            build_type=enums.BuildType.JUPYTER_STOP,
        ),
        tasks.check_compute_instance_status.s(
            user_project=workbench_stop_request.user_project,
            instance_name=workbench_stop_request.instance_name,
        ),
        tasks.handle_jupyter_workbench_stop_error.s(),
    )()
