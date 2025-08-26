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
from research_environment_api.modules.workbench_management import (
    entities,
    models as workbench_models,
)
from research_environment_api.modules.monitoring_management import (
    models,
    monitoring as monitoring_services,
)
from research_environment_api.modules.workspace_management.entities import (
    EntityScaffolding,
)
from research_environment_api.modules.workbench_management.utils import (
    format_gpu_accelerator_type,
    format_service_account_resource,
    add_iam_binding,
    remove_iam_binding,
)
from google.cloud.notebooks_v2.types import AcceleratorConfig

DEFAULT_APP_ENGINE_SERVICE_ID = "default"


def list_workbenches(
    gcp_project_id: str,
    workflows_in_progress: Iterable[models.WorkbenchActivity],
    user_email: Optional[str] = None,
    is_owner: bool = True,
) -> Iterable[Union[entities.Workbench, EntityScaffolding]]:
    gce_instances = _fetch_gce_instances(gcp_project_id)

    if not is_owner:
        shared_workbench_entries = _get_shared_workbenches_for_project(
            user_email, gcp_project_id, gce_instances
        )
        shared_workbenches = []
        if shared_workbench_entries:
            shared_workbenches = []
            for _, workbench in shared_workbench_entries:
                shared_workbenches.append(workbench)

        return shared_workbenches

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
    workbench_type = entities.WorkbenchType(workbench_creation.workbench_type)
    if workbench_type == entities.WorkbenchType.JUPYTER:
        return schedulers.create_jupyter_workbench(workbench_creation)
    elif workbench_type == entities.WorkbenchType.COLLABORATIVE:
        return schedulers.create_collaborative_workbench(workbench_creation)
    elif workbench_type == entities.WorkbenchType.RSTUDIO:
        return schedulers.create_rstudio_workbench(workbench_creation)
    else:
        raise ValueError(f"Unknown workbench type: {workbench_creation.workbench_type}")


def schedule_workbench_stop(workbench_stop_request: entities.WorkbenchToggleState):
    workbench_type = entities.WorkbenchType(workbench_stop_request.workbench_type)
    if workbench_type == entities.WorkbenchType.JUPYTER:
        return schedulers.stop_jupyter_workbench(workbench_stop_request)
    elif workbench_type == entities.WorkbenchType.COLLABORATIVE:
        return schedulers.stop_collaborative_workbench(workbench_stop_request)
    elif workbench_type == entities.WorkbenchType.RSTUDIO:
        return schedulers.stop_compute_engine_workbench(workbench_stop_request)
    else:
        raise ValueError(
            f"Unknown workbench type: {workbench_stop_request.workbench_type}"
        )


def schedule_workbench_start(workbench_start_request: entities.WorkbenchToggleState):
    workbench_type = entities.WorkbenchType(workbench_start_request.workbench_type)
    if workbench_type == entities.WorkbenchType.JUPYTER:
        return schedulers.start_jupyter_workbench(workbench_start_request)
    elif workbench_type == entities.WorkbenchType.COLLABORATIVE:
        return schedulers.start_collaborative_workbench(workbench_start_request)
    elif workbench_type == entities.WorkbenchType.RSTUDIO:
        return schedulers.start_rstudio_workbench(workbench_start_request)
    else:
        raise ValueError(
            f"Unknown workbench type: {workbench_start_request.workbench_type}"
        )


def schedule_workbench_update(
    workbench_update_request: entities.WorkbenchUpdate,
):
    workbench_type = entities.WorkbenchType(workbench_update_request.workbench_type)
    if workbench_type == entities.WorkbenchType.JUPYTER:
        return schedulers.update_jupyter_workbench(workbench_update_request)
    elif workbench_type == entities.WorkbenchType.COLLABORATIVE:
        return schedulers.update_collaborative_workbench(workbench_update_request)
    elif workbench_type == entities.WorkbenchType.RSTUDIO:
        return schedulers.update_rstudio_workbench(workbench_update_request)
    else:
        raise ValueError(
            f"Unknown workbench type: {workbench_update_request.workbench_type}"
        )


def schedule_workbench_destroy(
    workbench_destroy_request: entities.WorkbenchDestroy,
):
    workbench_type = entities.WorkbenchType(workbench_destroy_request.workbench_type)
    if workbench_type == entities.WorkbenchType.JUPYTER:
        return schedulers.destroy_jupyter_workbench(workbench_destroy_request)
    elif workbench_type == entities.WorkbenchType.COLLABORATIVE:
        return schedulers.destroy_collaborative_workbench(workbench_destroy_request)
    elif workbench_type == entities.WorkbenchType.RSTUDIO:
        return schedulers.destroy_rstudio_workbench(workbench_destroy_request)
    else:
        raise ValueError(
            f"Unknown workbench type: {workbench_destroy_request.workbench_type}"
        )


def generate_resource_name_from_dataset_identifier(dataset_identifier: str) -> str:
    return f"{dataset_identifier[:10]}-{''.join(random.choices(string.ascii_lowercase, k=5))}"


def get_available_zones(region: str) -> Tuple[str, Iterable[str]]:
    zones = constants.AVAILABLE_ZONES[region]
    zone, *fallback_zones = random.sample(zones, len(zones))
    return zone, *fallback_zones


def start_stopped_workbenches(folder_id: str):
    projects_client = app.config.google_cloud_resource_client

    active_project_ids = [
        project.project_id
        for project in projects_client.list_projects(parent=f"folders/{folder_id}")
        if project.state == google.cloud.resourcemanager.Project.State.ACTIVE
    ]

    notebooks_client = app.config.google_cloud_notebooks_client
    instances_to_start = []

    for project_id in active_project_ids:
        for region, zones in constants.AVAILABLE_ZONES.items():
            for zone in zones:
                for nb_instance in notebooks_client.list_instances(
                    parent=f"projects/{project_id}/locations/{zone}"
                ):
                    if (
                        nb_instance.state
                        != google.cloud.notebooks_v2.types.instance.State.STOPPED
                    ):
                        continue

                    update_time = nb_instance.update_time
                    current_time = datetime.now(timezone.utc)
                    if current_time - update_time > timedelta(days=3):
                        continue

                    instances_to_start.append(nb_instance.name)

    for instance_name in instances_to_start:
        notebooks_client.start_instance({"name": instance_name})

    return f"Started {len(instances_to_start)} instances."


def add_collaborators_to_workbench(
    add_collaborator_request: entities.WorkbenchCollaboratorModification,
):
    workspace_project_id = add_collaborator_request.workspace_project_id
    service_account_name = add_collaborator_request.service_account_name
    collaborators = add_collaborator_request.collaborators
    role = "roles/iam.serviceAccountUser"

    iam_client = app.config.google_iam_client

    resource = format_service_account_resource(
        workspace_project_id, service_account_name
    )

    with app.database_session() as session:
        with session.begin():
            for email in collaborators:
                try:
                    binding_added = add_iam_binding(iam_client, resource, email, role)

                    existing_record = (
                        session.query(workbench_models.WorkbenchCollaboratorData)
                        .filter_by(
                            workspace_project_id=workspace_project_id,
                            service_account_name=service_account_name,
                            collaborator_email=email,
                        )
                        .first()
                    )

                    if existing_record:
                        existing_record.status = (
                            workbench_models.CollaboratorStatus.SUCCESS
                        )
                        existing_record.viewed = False
                    else:
                        collaborator_data = workbench_models.WorkbenchCollaboratorData(
                            workspace_project_id=workspace_project_id,
                            service_account_name=service_account_name,
                            collaborator_email=email,
                            viewed=False,
                            status=workbench_models.CollaboratorStatus.SUCCESS,
                        )
                        session.add(collaborator_data)

                except Exception as e:
                    collaborator_data = workbench_models.WorkbenchCollaboratorData(
                        workspace_project_id=workspace_project_id,
                        service_account_name=service_account_name,
                        collaborator_email=email,
                        viewed=False,
                        status=workbench_models.CollaboratorStatus.FAILED,
                    )
                    session.add(collaborator_data)


def remove_collaborators_from_workbench(
    remove_collaborator_request: entities.WorkbenchCollaboratorModification,
):
    workspace_project_id = remove_collaborator_request.workspace_project_id
    service_account_name = remove_collaborator_request.service_account_name
    collaborators = remove_collaborator_request.collaborators
    role = "roles/iam.serviceAccountUser"

    iam_client = app.config.google_iam_client

    resource = format_service_account_resource(
        workspace_project_id, service_account_name
    )

    with app.database_session() as session:
        with session.begin():
            for email in collaborators:
                existing_record = (
                    session.query(workbench_models.WorkbenchCollaboratorData)
                    .filter_by(
                        workspace_project_id=workspace_project_id,
                        service_account_name=service_account_name,
                        collaborator_email=email,
                    )
                    .first()
                )
                try:
                    binding_removed = remove_iam_binding(
                        iam_client, resource, email, role
                    )

                    if existing_record:
                        existing_record.status = (
                            workbench_models.CollaboratorStatus.REMOVED
                        )
                        existing_record.viewed = True

                except Exception as e:
                    if existing_record:
                        existing_record.status = (
                            workbench_models.CollaboratorStatus.FAILED
                        )


def get_workbench_collaborators(
    get_collaborators_request: entities.WorkbenchGetCollaborators,
):
    workspace_project_id = get_collaborators_request.workspace_project_id
    service_account_name = get_collaborators_request.service_account_name

    with app.database_session() as session:
        collaborator_records = (
            session.query(workbench_models.WorkbenchCollaboratorData)
            .filter_by(
                workspace_project_id=workspace_project_id,
                service_account_name=service_account_name,
                status=workbench_models.CollaboratorStatus.SUCCESS,
            )
            .all()
        )

        collaborators = [record.collaborator_email for record in collaborator_records]
        return {"collaborators": collaborators}


def get_workbench_notifications(
    get_notifications_request: entities.WorkbenchGetNotifications,
):
    workspace_project_id = get_notifications_request.workspace_project_id
    service_account_name = get_notifications_request.service_account_name

    with app.database_session() as session:
        notification_records = (
            session.query(workbench_models.WorkbenchCollaboratorData)
            .filter_by(
                workspace_project_id=workspace_project_id,
                service_account_name=service_account_name,
                viewed=False,
                status=workbench_models.CollaboratorStatus.FAILED,
            )
            .order_by(workbench_models.WorkbenchCollaboratorData.created_at.desc())
            .limit(5)
            .all()
        )

        notifications = [
            {
                "id": record.id,
                "email": record.collaborator_email,
                "timestamp": record.created_at.isoformat(),
            }
            for record in notification_records
        ]

        return {"notifications": notifications}


def mark_notification_as_viewed(notification_id: str):
    with app.database_session() as session:
        with session.begin():
            notification = (
                session.query(workbench_models.WorkbenchCollaboratorData)
                .filter_by(id=notification_id)
                .first()
            )

            if notification:
                notification.viewed = True
                return True
            return False


def clear_all_notifications(
    clear_notifications_request: entities.WorkbenchClearNotifications,
):
    workspace_project_id = clear_notifications_request.workspace_project_id
    service_account_name = clear_notifications_request.service_account_name

    with app.database_session() as session:
        with session.begin():
            (
                session.query(workbench_models.WorkbenchCollaboratorData)
                .filter_by(
                    workspace_project_id=workspace_project_id,
                    service_account_name=service_account_name,
                    viewed=False,
                    status=workbench_models.CollaboratorStatus.FAILED,
                )
                .update({"viewed": True})
            )

        return True


def _get_shared_workbenches_for_project(
    email: str, gcp_project_id: str, gce_instances: Iterable[ComputeEngineInstance]
) -> list:
    username = email.split("@")[0]

    with app.database_session() as session:
        with session.begin():
            collaborator_entries = (
                session.query(workbench_models.WorkbenchCollaboratorData)
                .filter_by(
                    collaborator_email=email,
                    status=workbench_models.CollaboratorStatus.SUCCESS,
                    workspace_project_id=gcp_project_id,
                )
                .all()
            )
            workbench_keys = set(
                (entry.workspace_project_id, entry.service_account_name)
                for entry in collaborator_entries
            )

    shared_workbenches = []
    for _, service_account_name in workbench_keys:
        try:
            for instance in gce_instances:
                wb = entities.Workbench.from_gce_instance(instance, [])
                if (
                    wb.service_account_name == service_account_name
                    and wb.workbench_owner_username != username
                ):
                    shared_workbenches.append((gcp_project_id, wb))
        except Exception as e:
            continue

    return shared_workbenches
