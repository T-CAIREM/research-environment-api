import random
import string
from typing import Iterable, Optional, Tuple, Union

from google import api_core
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance

from research_environment_api.background import enums, schedulers, constants
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import entities
from research_environment_api.modules.monitoring_management import (
    models,
    monitoring as monitoring_services,
)
from research_environment_api.modules.workspace_management.entities import (
    EntityScaffolding,
)

DEFAULT_APP_ENGINE_SERVICE_ID = "default"


def list_workbenches(
    gcp_project_id: str,
    workflows_in_progress: Iterable[models.WorkbenchActivity],
) -> Iterable[Union[entities.Workbench, EntityScaffolding]]:
    gce_instances = _fetch_gce_instances(gcp_project_id)

    provisioned_workbenches = [
        entities.Workbench.from_gce_instance(instance, workflows_in_progress)
        for instance in gce_instances
    ]

    provisioned_workbench_ids = [workbench.id for workbench in provisioned_workbenches]

    workbench_scaffoldings = [
        EntityScaffolding(
            id=workflow.id,
            gcp_project_id=workflow.workspace_id,
            status=entities.WorkbenchStatus.CREATING,
        )
        for workflow in workflows_in_progress
        if workflow.workspace_id == gcp_project_id
        and workflow.build_type == enums.BuildType.WORKBENCH_CREATION
        and workflow.workbench_id not in provisioned_workbench_ids
    ]
    return provisioned_workbenches + workbench_scaffoldings


def get_compute_engine_workbench(
    gcp_project_id: str,
    instance_name: str,
    user_email: str,
) -> entities.Workbench:
    # The API exposes instance IDs as strings for compatibility reasons.
    gce_instances = _fetch_gce_instances(gcp_project_id)
    gce_instance = next(
        filter(lambda instance: instance.name == instance_name, gce_instances)
    )
    workflows_in_progress = monitoring_services.list_active_workflows(user_email)
    return entities.Workbench.from_gce_instance(gce_instance, workflows_in_progress)


def _fetch_gce_instances(gcp_project_id: str) -> Iterable[ComputeEngineInstance]:
    try:
        gce_instances_per_zone = (
            app.config.google_compute_engine_instances_client.aggregated_list(
                project=gcp_project_id
            )
        )
    except api_core.exceptions.Forbidden as e:
        # HACK: Workspaces in the middle of provisioning are visible but do not have the required APIs enabled yet.
        if "Compute Engine API has not been used in project" in e.message:
            return []
        else:
            raise e

    return [
        instance
        for zone, instances_in_region in gce_instances_per_zone
        for instance in instances_in_region.instances
    ]


def schedule_workbench_create(
    workbench_creation: entities.WorkbenchCreate,
):
    if workbench_creation.workbench_type == "jupyter":
        return schedulers.create_jupyter_workbench(workbench_creation)
    else:
        return schedulers.create_rstudio_workbench(workbench_creation)


def schedule_workbench_stop(workbench_stop_request: entities.WorkbenchToggleState):
    if workbench_stop_request.workbench_type == "jupyter":
        return schedulers.stop_jupyter_workbench(workbench_stop_request)
    else:
        return schedulers.stop_compute_engine_workbench(workbench_stop_request)


def schedule_workbench_start(workbench_start_request: entities.WorkbenchToggleState):
    if workbench_start_request.workbench_type == "jupyter":
        return schedulers.start_jupyter_workbench(workbench_start_request)
    else:
        return schedulers.start_rstudio_workbench(workbench_start_request)


def schedule_workbench_update(
    workbench_update_request: entities.WorkbenchUpdate,
):
    if workbench_update_request.workbench_type == "jupyter":
        return schedulers.update_jupyter_workbench(workbench_update_request)
    else:
        return schedulers.update_rstudio_workbench(workbench_update_request)


def schedule_workbench_destroy(
    workbench_destroy_request: entities.WorkbenchDestroy,
):
    if workbench_destroy_request.workbench_type == "jupyter":
        return schedulers.destroy_jupyter_workbench(workbench_destroy_request)
    else:
        return schedulers.destroy_rstudio_workbench(workbench_destroy_request)


def generate_resource_name_from_dataset_identifier(dataset_identifier: str) -> str:
    return f"{dataset_identifier[:10]}-{''.join(random.choices(string.ascii_lowercase, k=5))}"


def get_available_zones(region: str) -> Tuple[str, Iterable[str]]:
    zones = constants.AVAILABLE_ZONES[region]
    zone, *fallback_zones = random.sample(zones, len(zones))
    return zone, *fallback_zones
