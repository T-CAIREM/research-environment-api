import random
import string
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Tuple, Union

from google import api_core
from google.cloud.compute_v1.types.compute import Instance as ComputeEngineInstance
import google.cloud.resourcemanager_v3
import google.cloud.notebooks_v2
from google.iam.v1 import policy_pb2

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
from research_environment_api.modules.workbench_management.utils import (
    format_gpu_accelerator_type,
)
from google.cloud.notebooks_v2.types import AcceleratorConfig

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


def validate_gpu_accelerator(project_id: str, name: str, workbench_type: str) -> bool:
    if workbench_type in ["jupyter", "collaborative"]:

        valid_accelerators = {
            key
            for key in AcceleratorConfig.AcceleratorType.__members__.keys()
            if key != "ACCELERATOR_TYPE_UNSPECIFIED"
        }

        formatted_name = format_gpu_accelerator_type(name)
        return formatted_name in valid_accelerators

    elif workbench_type == "rstudio":
        client = app.config.google_compute_engine_accelerator_types_client
        response = client.aggregated_list(project=project_id)
        available_gpus = set()
        for zone, accelerator_types_scoped_list in response:
            if hasattr(accelerator_types_scoped_list, "accelerator_types"):
                for accelerator in accelerator_types_scoped_list.accelerator_types:
                    available_gpus.add(accelerator.name)

        return name in available_gpus

    else:
        raise ValueError(f"Unknown workbench type: {workbench_type}")


def schedule_workbench_create(
    workbench_creation: entities.WorkbenchCreate,
):
    if workbench_creation.workbench_type == "jupyter":
        return schedulers.create_jupyter_workbench(workbench_creation)
    elif workbench_creation.workbench_type == "collaborative":
        return schedulers.create_collaborative_workbench(workbench_creation)
    else:
        return schedulers.create_rstudio_workbench(workbench_creation)


def schedule_workbench_stop(workbench_stop_request: entities.WorkbenchToggleState):
    if workbench_stop_request.workbench_type == "jupyter":
        return schedulers.stop_jupyter_workbench(workbench_stop_request)
    elif workbench_stop_request.workbench_type == "collaborative":
        return schedulers.stop_collaborative_workbench(workbench_stop_request)
    else:
        return schedulers.stop_compute_engine_workbench(workbench_stop_request)


def schedule_workbench_start(workbench_start_request: entities.WorkbenchToggleState):
    if workbench_start_request.workbench_type == "jupyter":
        return schedulers.start_jupyter_workbench(workbench_start_request)
    elif workbench_start_request.workbench_type == "collaborative":
        return schedulers.start_collaborative_workbench(workbench_start_request)
    else:
        return schedulers.start_rstudio_workbench(workbench_start_request)


def schedule_workbench_update(
    workbench_update_request: entities.WorkbenchUpdate,
):
    if workbench_update_request.workbench_type == "jupyter":
        return schedulers.update_jupyter_workbench(workbench_update_request)
    elif workbench_update_request.workbench_type == "collaborative":
        return schedulers.update_collaborative_workbench(workbench_update_request)
    else:
        return schedulers.update_rstudio_workbench(workbench_update_request)


def schedule_workbench_destroy(
    workbench_destroy_request: entities.WorkbenchDestroy,
):
    if workbench_destroy_request.workbench_type == "jupyter":
        return schedulers.destroy_jupyter_workbench(workbench_destroy_request)
    elif workbench_destroy_request.workbench_type == "collaborative":
        return schedulers.destroy_collaborative_workbench(workbench_destroy_request)
    else:
        return schedulers.destroy_rstudio_workbench(workbench_destroy_request)


def generate_resource_name_from_dataset_identifier(dataset_identifier: str) -> str:
    return f"{dataset_identifier[:10]}-{''.join(random.choices(string.ascii_lowercase, k=5))}"


def get_available_zones(region: str) -> Tuple[str, Iterable[str]]:
    zones = constants.AVAILABLE_ZONES[region]
    zone, *fallback_zones = random.sample(zones, len(zones))
    return zone, *fallback_zones


def start_stopped_workbenches(folder_id: str):
    projects_client = app.config.google_cloud_resource_client

    project_ids = []
    for project in projects_client.list_projects(parent=f"folders/{folder_id}"):
        if project.state == google.cloud.resourcemanager.Project.State.ACTIVE:
            project_ids.append((project.project_id, project.labels["region"]))

    notebooks_client = app.config.google_cloud_notebooks_client
    instances_to_start = []
    for project_id, region in project_ids:
        if region == "":
            continue

        for zone in constants.AVAILABLE_ZONES.get(region, ""):
            for instance in notebooks_client.list_instances(
                parent=f"projects/{project_id}/locations/{zone}"
            ):
                if (
                    instance.state
                    != google.cloud.notebooks_v2.types.instance.State.STOPPED
                ):
                    continue

                update_time = instance.update_time
                current_time = datetime.now(timezone.utc)
                if current_time - update_time > timedelta(days=3):
                    continue

                instances_to_start.append(instance.name)

    for instance_name in instances_to_start:
        notebooks_client.start_instance(
            {"name": instance_name},
        )

    return f"Started {len(instances_to_start)} instances."


def add_collaborators_to_workbench(
    add_collaborator_request: entities.WorkbenchCollaborator,
):
    """Adds the `roles/iam.serviceAccountUser` role to each user in the list"""
    project_id = add_collaborator_request.project_id
    service_account_name = add_collaborator_request.service_account_name
    user_emails = add_collaborator_request.user_emails
    role = "roles/iam.serviceAccountUser"

    iam_client = app.config.google_iam_client
    resource = f"projects/{project_id}/serviceAccounts/{service_account_name}@{project_id}.iam.gserviceaccount.com"

    for email in user_emails:
        user_member = f"user:{email}"

        try:
            policy = iam_client.get_iam_policy(request={"resource": resource})
            bindings = policy.bindings

            role_binding = next((b for b in bindings if b.role == role), None)

            if role_binding:
                if user_member in role_binding.members:
                    continue
                role_binding.members.append(user_member)
            else:
                bindings.append(policy_pb2.Binding(role=role, members=[user_member]))
            updated_policy = policy_pb2.Policy(bindings=bindings)
            iam_client.set_iam_policy(
                request={"resource": resource, "policy": updated_policy}
            )

        except Exception as e:
            continue
