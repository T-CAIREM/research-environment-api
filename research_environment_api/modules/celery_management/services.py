from research_environment_api.modules.celery_management import (
    tasks,
    factories,
    internal,
    enums,
)
from research_environment_api.modules.config import config

from celery import chain


def start_jupyter_notebook(workbench_creation_request):
    zone, available_zones = internal.get_available_zones(
        workbench_creation_request.region
    )

    build = factories.BuildFactory(
        config.project_id, internal.create_cloud_build_source()
    ).create_jupyter(
        machine_type=workbench_creation_request.machine_type,
        user_project_id=workbench_creation_request.user_project_id,
        dataset=workbench_creation_request.dataset,
        email_id=workbench_creation_request.email_id,
        bucket_name=workbench_creation_request.bucket_name,
        region=workbench_creation_request.region,
        persistent_disk=workbench_creation_request.persistent_disk,
        gpu_accelerator=workbench_creation_request.gpu_accelerator,
        vm_image=workbench_creation_request.vm_image,
        zone=zone,
        jupyter_startup_script_bucket=workbench_creation_request.jupyter_startup_script_bucket,
    )
    return chain(
        tasks.start_cloud_build.s(
            build=build, build_type=enums.BuildType.JUPYTER_CREATION
        ),
        tasks.check_cloud_build_status.s(),
        tasks.handle_jupyter_workbench_build_error.s(available_zones, build),
    )()
