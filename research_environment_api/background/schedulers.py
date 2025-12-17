import random
import uuid

from research_environment_api.background import builds, enums, workflows
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management import (
    entities,
    services,
)
from research_environment_api.modules.monitoring_management import (
    models as monitoring_models,
)
from research_environment_api.modules.workspace_management import (
    entities as workspace_entities,
)
from research_environment_api.modules.sharing_management.services import (
    specify_buckets_fusing_permissions,
)
from research_environment_api.modules.user_group_management import (
    services as user_group_services,
)
from research_environment_api.modules.monitoring_management import (
    services as monitoring_services,
)
from research_environment_api.modules.monitoring_management.entities import (
    GeneralQuotaMetrics,
)


def create_jupyter_workbench(
    workbench_creation_request: entities.WorkbenchCreate,
) -> uuid.UUID:
    zone, *fallback_zones = services.get_available_zones(
        workbench_creation_request.region
    )
    shared_bucket_user_permissions_dict = specify_buckets_fusing_permissions(
        workbench_creation_request.sharing_bucket_identifiers,
        workbench_creation_request.user_email,
    )
    dataset_identifier = workbench_creation_request.dataset_identifier
    workbench_id = f"jupyter-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    service_account_name = f"jupyter-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    user_permissions_list = user_group_services.get_user_permissions(
        workbench_creation_request.organization_id,
        workbench_creation_request.user_groups,
    )

    build = builds.create_jupyter_workbench_build(
        instance_name=workbench_id,
        workspace_project_id=workbench_creation_request.workspace_project_id,
        service_account_name=service_account_name,
        region=workbench_creation_request.region,
        zone=zone,
        machine_type=workbench_creation_request.machine_type,
        disk_size=workbench_creation_request.disk_size,
        gpu_accelerator_type=workbench_creation_request.gpu_accelerator_type,
        dataset_identifier=workbench_creation_request.dataset_identifier,
        user_email=workbench_creation_request.user_email,
        bucket_name=workbench_creation_request.bucket_name,
        vm_image=workbench_creation_request.vm_image,
        sharing_bucket_permission_dict=shared_bucket_user_permissions_dict,
        user_permissions_list=user_permissions_list,
        collaborative=workbench_creation_request.collaborative,
        associated_event=workbench_creation_request.associated_event,
    )

    monitoring_services.clear_quotas_cache(
        workbench_creation_request.workspace_project_id,
        workbench_creation_request.region,
        GeneralQuotaMetrics,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                build_type=enums.BuildType.WORKBENCH_CREATION,
                invoker_email=workbench_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workspace_id=workbench_creation_request.workspace_project_id,
                workbench_id=workbench_id,
            )
            session.add(workbench_activity)

            workflows.create_jupyter_workbench(
                build=build,
                user_email=workbench_creation_request.user_email,
                workspace_project_id=workbench_creation_request.workspace_project_id,
                instance_zone=zone,
                instance_name=workbench_id,
                fallback_zones=fallback_zones,
                workbench_activity_id=workbench_activity.id,
                dataset_identifier=workbench_creation_request.dataset_identifier,
            )()

            return workbench_activity.id


def create_collaborative_workbench(
    workbench_creation_request: entities.WorkbenchCreate,
) -> uuid.UUID:
    zone, *fallback_zones = services.get_available_zones(
        workbench_creation_request.region
    )
    shared_bucket_user_permissions_dict = specify_buckets_fusing_permissions(
        workbench_creation_request.sharing_bucket_identifiers,
        workbench_creation_request.user_email,
    )
    dataset_identifier = workbench_creation_request.dataset_identifier
    workbench_id = f"collaborative-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    service_account_name = f"collaborative-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    user_permissions_list = user_group_services.get_user_permissions(
        workbench_creation_request.organization_id,
        workbench_creation_request.user_groups,
    )

    build = builds.create_collaborative_workbench_build(
        instance_name=workbench_id,
        workspace_project_id=workbench_creation_request.workspace_project_id,
        service_account_name=service_account_name,
        region=workbench_creation_request.region,
        zone=zone,
        machine_type=workbench_creation_request.machine_type,
        disk_size=workbench_creation_request.disk_size,
        gpu_accelerator_type=workbench_creation_request.gpu_accelerator_type,
        dataset_identifier=workbench_creation_request.dataset_identifier,
        user_email=workbench_creation_request.user_email,
        bucket_name=workbench_creation_request.bucket_name,
        vm_image=workbench_creation_request.vm_image,
        sharing_bucket_permission_dict=shared_bucket_user_permissions_dict,
        user_permissions_list=user_permissions_list,
        collaborative=workbench_creation_request.collaborative,
        associated_event=workbench_creation_request.associated_event,
    )

    monitoring_services.clear_quotas_cache(
        workbench_creation_request.workspace_project_id,
        workbench_creation_request.region,
        GeneralQuotaMetrics,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                build_type=enums.BuildType.WORKBENCH_CREATION,
                invoker_email=workbench_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workspace_id=workbench_creation_request.workspace_project_id,
                workbench_id=workbench_id,
            )
            session.add(workbench_activity)

            workflows.create_collaborative_workbench(
                build=build,
                user_email=workbench_creation_request.user_email,
                workspace_project_id=workbench_creation_request.workspace_project_id,
                instance_zone=zone,
                instance_name=workbench_id,
                fallback_zones=fallback_zones,
                workbench_activity_id=workbench_activity.id,
                dataset_identifier=workbench_creation_request.dataset_identifier,
                collaborators=workbench_creation_request.collaborators,
            )()

            return workbench_activity.id


def create_workspace(
    workspace_creation_request: workspace_entities.WorkspaceCreation,
) -> uuid.UUID:
    user_permissions_list = user_group_services.get_user_permissions(
        workspace_creation_request.organization_id,
        workspace_creation_request.user_groups,
    )

    build = builds.create_workspace_build(
        billing_account_id=workspace_creation_request.billing_account_id,
        workspace_project_id=workspace_creation_request.workspace_project_id,
        user_email=workspace_creation_request.user_email,
        user_permissions_list=user_permissions_list,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workspace_id=workspace_creation_request.workspace_project_id,
                invoker_email=workspace_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                build_type=enums.BuildType.WORKSPACE_CREATION,
            )
            session.add(workbench_activity)

            workflows.create_workspace(
                build=build,
                user_email=workspace_creation_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def create_shared_workspace(
    shared_workspace_creation_request: workspace_entities.SharedWorkspaceCreation,
) -> uuid.UUID:
    build = builds.create_shared_workspace_build(
        billing_account_id=shared_workspace_creation_request.billing_account_id,
        workspace_project_id=shared_workspace_creation_request.workspace_project_id,
        user_email=shared_workspace_creation_request.user_email,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workspace_id=shared_workspace_creation_request.workspace_project_id,
                invoker_email=shared_workspace_creation_request.user_email,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                build_type=enums.BuildType.SHARED_WORKSPACE_CREATION,
            )
            session.add(workbench_activity)

            workflows.create_workspace(
                build=build,
                user_email=shared_workspace_creation_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def destroy_workspace(
    workspace_deletion_request: workspace_entities.WorkspaceDeletion,
) -> uuid.UUID:
    build = builds.destroy_workspace_build(
        billing_account_id=workspace_deletion_request.billing_account_id,
        workspace_project_id=workspace_deletion_request.workspace_project_id,
        user_email=workspace_deletion_request.user_email,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                invoker_email=workspace_deletion_request.user_email,
                workspace_id=workspace_deletion_request.workspace_project_id,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                build_type=enums.BuildType.WORKSPACE_DELETION,
            )
            session.add(workbench_activity)

            workflows.destroy_workspace(
                build=build,
                user_email=workspace_deletion_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def destroy_shared_workspace(
    shared_workspace_deletion_request: workspace_entities.SharedWorkspaceDeletion,
) -> uuid.UUID:
    build = builds.destroy_shared_workspace_build(
        billing_account_id=shared_workspace_deletion_request.billing_account_id,
        workspace_project_id=shared_workspace_deletion_request.workspace_project_id,
        user_email=shared_workspace_deletion_request.user_email,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                invoker_email=shared_workspace_deletion_request.user_email,
                workspace_id=shared_workspace_deletion_request.workspace_project_id,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                build_type=enums.BuildType.SHARED_WORKSPACE_DELETION,
            )
            session.add(workbench_activity)

            workflows.destroy_workspace(
                build=build,
                user_email=shared_workspace_deletion_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def stop_compute_engine_workbench(
    workbench_stop_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_stop_request.workspace_project_id,
        instance_name=workbench_stop_request.workbench_resource_id,
        user_email=workbench_stop_request.user_email,
    )

    monitoring_services.clear_quotas_cache(
        workbench_stop_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_stop_request.workspace_project_id,
                invoker_email=workbench_stop_request.user_email,
                build_type=enums.BuildType.WORKBENCH_STOP,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.stop_compute_engine_workbench(
                workspace_project_id=workbench_stop_request.workspace_project_id,
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def stop_jupyter_workbench(
    workbench_stop_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_stop_request.workspace_project_id,
        instance_name=workbench_stop_request.workbench_resource_id,
        user_email=workbench_stop_request.user_email,
    )

    monitoring_services.clear_quotas_cache(
        workbench_stop_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_stop_request.workspace_project_id,
                invoker_email=workbench_stop_request.user_email,
                build_type=enums.BuildType.WORKBENCH_STOP,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.stop_jupyter_workbench(
                workspace_project_id=workbench_stop_request.workspace_project_id,
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def start_jupyter_workbench(
    workbench_start_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_start_request.workspace_project_id,
        instance_name=workbench_start_request.workbench_resource_id,
        user_email=workbench_start_request.user_email,
    )

    monitoring_services.clear_quotas_cache(
        workbench_start_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_start_request.workspace_project_id,
                invoker_email=workbench_start_request.user_email,
                build_type=enums.BuildType.WORKBENCH_START,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.start_jupyter_workbench(
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workspace_project_id=workbench_start_request.workspace_project_id,
                workbench_activity_id=workbench_activity.id,
                dataset_identifier=workbench.dataset_identifier,
            )()

            return workbench_activity.id


def update_jupyter_workbench(
    workbench_update_request: entities.WorkbenchUpdate,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_update_request.workspace_project_id,
        instance_name=workbench_update_request.workbench_resource_id,
        user_email=workbench_update_request.user_email,
    )

    shared_bucket_user_permissions_dict = specify_buckets_fusing_permissions(
        workbench.sharing_bucket_identifiers,
        workbench_update_request.user_email,
    )

    monitoring_services.clear_quotas_cache(
        workbench_update_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    monitoring_services.check_workbench_update_quotas(
        workbench_update_request.workspace_project_id,
        workbench.region,
        workbench_update_request.machine_type,
    )
    build = builds.update_jupyter_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        instance_name=workbench.id,
        machine_type=workbench_update_request.machine_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        sharing_bucket_permission_dict=shared_bucket_user_permissions_dict,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_update_request.workspace_project_id,
                invoker_email=workbench_update_request.user_email,
                build_type=enums.BuildType.WORKBENCH_UPDATE,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.update_jupyter_workbench(
                build=build,
                workspace_project_id=workbench_update_request.workspace_project_id,
                instance_zone=workbench.zone,
                instance_name=workbench.id,
                user_email=workbench_update_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def destroy_jupyter_workbench_flow(
    workbench_destroy_request: entities.WorkbenchDestroy, workbench: entities.Workbench
) -> uuid.UUID:
    monitoring_services.clear_quotas_cache(
        workbench_destroy_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    build = builds.destroy_jupyter_workbench_build(
        workspace_project_id=workbench_destroy_request.workspace_project_id,
        instance_name=workbench.id,
        user_email=workbench_destroy_request.user_email,
        region=workbench.region,
        machine_type=workbench.machine_type,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        service_account_name=workbench.service_account_name,
        sharing_bucket_identifiers=workbench.sharing_bucket_identifiers,
        collaborative=workbench_destroy_request.collaborative,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_destroy_request.workspace_project_id,
                invoker_email=workbench_destroy_request.user_email,
                build_type=enums.BuildType.WORKBENCH_DESTROY,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.destroy_jupyter_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                user_email=workbench_destroy_request.user_email,
            )()

            return workbench_activity.id


def destroy_jupyter_workbench(
    workbench_destroy_request: entities.WorkbenchDestroy,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_destroy_request.workspace_project_id,
        instance_name=workbench_destroy_request.workbench_resource_id,
        user_email=workbench_destroy_request.user_email,
    )

    destroy_jupyter_workbench_flow(workbench_destroy_request, workbench)


def stop_collaborative_workbench(
    workbench_stop_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_stop_request.workspace_project_id,
        instance_name=workbench_stop_request.workbench_resource_id,
        user_email=workbench_stop_request.user_email,
    )

    monitoring_services.clear_quotas_cache(
        workbench_stop_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_stop_request.workspace_project_id,
                invoker_email=workbench_stop_request.user_email,
                build_type=enums.BuildType.WORKBENCH_STOP,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.stop_collaborative_workbench(
                workspace_project_id=workbench_stop_request.workspace_project_id,
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def start_collaborative_workbench(
    workbench_start_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_start_request.workspace_project_id,
        instance_name=workbench_start_request.workbench_resource_id,
        user_email=workbench_start_request.user_email,
    )

    monitoring_services.clear_quotas_cache(
        workbench_start_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_start_request.workspace_project_id,
                invoker_email=workbench_start_request.user_email,
                build_type=enums.BuildType.WORKBENCH_START,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.start_collaborative_workbench(
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workspace_project_id=workbench_start_request.workspace_project_id,
                workbench_activity_id=workbench_activity.id,
                dataset_identifier=workbench.dataset_identifier,
            )()

            return workbench_activity.id


def update_collaborative_workbench(
    workbench_update_request: entities.WorkbenchUpdate,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_update_request.workspace_project_id,
        instance_name=workbench_update_request.workbench_resource_id,
        user_email=workbench_update_request.user_email,
    )

    shared_bucket_user_permissions_dict = specify_buckets_fusing_permissions(
        workbench.sharing_bucket_identifiers,
        workbench_update_request.user_email,
    )

    monitoring_services.clear_quotas_cache(
        workbench_update_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    monitoring_services.check_workbench_update_quotas(
        workbench_update_request.workspace_project_id,
        workbench.region,
        workbench_update_request.machine_type,
    )
    build = builds.update_collaborative_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        instance_name=workbench.id,
        machine_type=workbench_update_request.machine_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        sharing_bucket_permission_dict=shared_bucket_user_permissions_dict,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_update_request.workspace_project_id,
                invoker_email=workbench_update_request.user_email,
                build_type=enums.BuildType.WORKBENCH_UPDATE,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.update_collaborative_workbench(
                build=build,
                workspace_project_id=workbench_update_request.workspace_project_id,
                instance_zone=workbench.zone,
                instance_name=workbench.id,
                user_email=workbench_update_request.user_email,
                workbench_activity_id=workbench_activity.id,
            )()

            return workbench_activity.id


def destroy_collaborative_workbench_flow(
    workbench_destroy_request: entities.WorkbenchDestroy, workbench: entities.Workbench
) -> uuid.UUID:
    monitoring_services.clear_quotas_cache(
        workbench_destroy_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    get_collaborators_request = entities.WorkbenchGetCollaborators(
        workspace_project_id=workbench_destroy_request.workspace_project_id,
        service_account_name=workbench.service_account_name,
    )

    collaborators_response = services.get_workbench_collaborators(
        get_collaborators_request
    )
    collaborators = collaborators_response.get("collaborators", [])

    if collaborators:
        remove_collaborator_request = entities.WorkbenchCollaboratorModification(
            workspace_project_id=workbench_destroy_request.workspace_project_id,
            service_account_name=workbench.service_account_name,
            collaborators=collaborators,
        )
        services.remove_collaborators_from_workbench(remove_collaborator_request)

    build = builds.destroy_collaborative_workbench_build(
        workspace_project_id=workbench_destroy_request.workspace_project_id,
        instance_name=workbench.id,
        user_email=workbench_destroy_request.user_email,
        region=workbench.region,
        machine_type=workbench.machine_type,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        service_account_name=workbench.service_account_name,
        sharing_bucket_identifiers=workbench.sharing_bucket_identifiers,
        collaborative=workbench_destroy_request.collaborative,
    )
    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_destroy_request.workspace_project_id,
                invoker_email=workbench_destroy_request.user_email,
                build_type=enums.BuildType.WORKBENCH_DESTROY,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.destroy_collaborative_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                user_email=workbench_destroy_request.user_email,
            )()

            return workbench_activity.id


def destroy_collaborative_workbench(
    workbench_destroy_request: entities.WorkbenchDestroy,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_destroy_request.workspace_project_id,
        instance_name=workbench_destroy_request.workbench_resource_id,
        user_email=workbench_destroy_request.user_email,
    )
    destroy_collaborative_workbench_flow(workbench_destroy_request, workbench)


def create_rstudio_workbench(
    workbench_creation_request: entities.WorkbenchCreate,
) -> uuid.UUID:
    zone, *fallback_zones = services.get_available_zones(
        workbench_creation_request.region
    )
    shared_bucket_user_permissions_dict = specify_buckets_fusing_permissions(
        workbench_creation_request.sharing_bucket_identifiers,
        workbench_creation_request.user_email,
    )
    dataset_identifier = workbench_creation_request.dataset_identifier
    workbench_id = f"rstudio-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    service_account_name = f"rstudio-{services.generate_resource_name_from_dataset_identifier(dataset_identifier)}"
    user_permissions_list = user_group_services.get_user_permissions(
        workbench_creation_request.organization_id,
        workbench_creation_request.user_groups,
    )

    monitoring_services.clear_quotas_cache(
        workbench_creation_request.workspace_project_id,
        workbench_creation_request.region,
        GeneralQuotaMetrics,
    )

    build = builds.create_rstudio_workbench_build(
        workspace_project_id=workbench_creation_request.workspace_project_id,
        workspace_numeric_id=workbench_creation_request.workspace_numeric_id,
        region=workbench_creation_request.region,
        zone=zone,
        machine_type=workbench_creation_request.machine_type,
        disk_size=workbench_creation_request.disk_size,
        instance_name=workbench_id,
        service_account_name=service_account_name,
        gpu_accelerator_type=workbench_creation_request.gpu_accelerator_type,
        dataset_identifier=workbench_creation_request.dataset_identifier,
        user_email=workbench_creation_request.user_email,
        bucket_name=workbench_creation_request.bucket_name,
        sharing_bucket_permission_dict=shared_bucket_user_permissions_dict,
        user_permissions_list=user_permissions_list,
        associated_event=workbench_creation_request.associated_event,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench_id,
                workspace_id=workbench_creation_request.workspace_project_id,
                invoker_email=workbench_creation_request.user_email,
                build_type=enums.BuildType.WORKBENCH_CREATION,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.create_rstudio_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                workspace_project_id=workbench_creation_request.workspace_project_id,
                instance_zone=zone,
                instance_name=workbench_id,
                user_email=workbench_creation_request.user_email,
                fallback_zones=fallback_zones,
                dataset_identifier=workbench_creation_request.dataset_identifier,
            )()

            return workbench_activity.id


def start_rstudio_workbench(
    workbench_start_request: entities.WorkbenchToggleState,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        gcp_project_id=workbench_start_request.workspace_project_id,
        instance_name=workbench_start_request.workbench_resource_id,
        user_email=workbench_start_request.user_email,
    )

    monitoring_services.clear_quotas_cache(
        workbench_start_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_start_request.workspace_project_id,
                invoker_email=workbench_start_request.user_email,
                build_type=enums.BuildType.WORKBENCH_START,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.start_rstudio_workbench(
                instance_name=workbench.id,
                instance_zone=workbench.zone,
                workspace_project_id=workbench_start_request.workspace_project_id,
                workbench_activity_id=workbench_activity.id,
                dataset_identifier=workbench.dataset_identifier,
            )()

            return workbench_activity.id


def update_rstudio_workbench(
    workbench_update_request: entities.WorkbenchUpdate,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        workbench_update_request.workspace_project_id,
        workbench_update_request.workbench_resource_id,
        workbench_update_request.user_email,
    )

    shared_bucket_user_permissions_dict = specify_buckets_fusing_permissions(
        workbench.sharing_bucket_identifiers,
        workbench_update_request.user_email,
    )

    user_permissions_list = (
        user_group_services.get_roles_associated_with_service_account(
            workbench.service_account_name,
            workbench_update_request.workspace_project_id,
        )
    )

    monitoring_services.clear_quotas_cache(
        workbench_update_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    monitoring_services.check_workbench_update_quotas(
        workbench_update_request.workspace_project_id,
        workbench.region,
        workbench_update_request.machine_type,
    )

    build = builds.update_rstudio_workbench_build(
        workspace_project_id=workbench_update_request.workspace_project_id,
        instance_name=workbench.id,
        machine_type=workbench_update_request.machine_type,
        user_email=workbench_update_request.user_email,
        region=workbench.region,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        brand_name=workbench.brand_name,
        service_account_name=workbench.service_account_name,
        sharing_bucket_permission_dict=shared_bucket_user_permissions_dict,
        user_permissions_list=user_permissions_list,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_update_request.workspace_project_id,
                invoker_email=workbench_update_request.user_email,
                build_type=enums.BuildType.WORKBENCH_UPDATE,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.update_rstudio_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                user_email=workbench_update_request.user_email,
            )()

            return workbench_activity.id


def destroy_rstudio_workbench_flow(
    workbench_destroy_request: entities.WorkbenchDestroy, workbench: entities.Workbench
) -> uuid.UUID:
    monitoring_services.clear_quotas_cache(
        workbench_destroy_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    build = builds.destroy_rstudio_workbench_build(
        workspace_project_id=workbench_destroy_request.workspace_project_id,
        instance_name=workbench.id,
        machine_type=workbench.machine_type,
        user_email=workbench_destroy_request.user_email,
        region=workbench.region,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        brand_name=workbench.brand_name,
        service_account_name=workbench.service_account_name,
        sharing_bucket_identifiers=workbench.sharing_bucket_identifiers,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_destroy_request.workspace_project_id,
                invoker_email=workbench_destroy_request.user_email,
                build_type=enums.BuildType.WORKBENCH_DESTROY,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.destroy_rstudio_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                user_email=workbench_destroy_request.user_email,
            )()

            return workbench_activity.id


def destroy_rstudio_workbench(
    workbench_destroy_request: entities.WorkbenchDestroy,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        workbench_destroy_request.workspace_project_id,
        workbench_destroy_request.workbench_resource_id,
        workbench_destroy_request.user_email,
    )
    destroy_rstudio_workbench_flow(workbench_destroy_request, workbench)


def renew_rstudio_ssl_certificate(
    workbench_renewal_request: entities.WorkbenchRenewSSLCertificate,
) -> uuid.UUID:
    workbench = services.get_compute_engine_workbench(
        workbench_renewal_request.workspace_project_id,
        workbench_renewal_request.workbench_resource_id,
        workbench_renewal_request.user_email,
    )

    shared_bucket_user_permissions_dict = specify_buckets_fusing_permissions(
        workbench.sharing_bucket_identifiers,
        workbench_renewal_request.user_email,
    )

    user_permissions_list = (
        user_group_services.get_roles_associated_with_service_account(
            workbench.service_account_name,
            workbench_renewal_request.workspace_project_id,
        )
    )

    monitoring_services.clear_quotas_cache(
        workbench_renewal_request.workspace_project_id,
        workbench.region,
        GeneralQuotaMetrics,
    )

    monitoring_services.check_workbench_update_quotas(
        workbench_renewal_request.workspace_project_id,
        workbench.region,
        workbench.machine_type,
    )

    build = builds.update_rstudio_workbench_build(
        workspace_project_id=workbench_renewal_request.workspace_project_id,
        instance_name=workbench.id,
        machine_type=workbench.machine_type,
        user_email=workbench_renewal_request.user_email,
        region=workbench.region,
        disk_size=workbench.disk_size,
        gpu_accelerator_type=workbench.gpu_accelerator_type,
        dataset_identifier=workbench.dataset_identifier,
        bucket_name=workbench.bucket_name,
        zone=workbench.zone,
        vm_image=workbench.vm_image,
        brand_name=workbench.brand_name,
        service_account_name=workbench.service_account_name,
        sharing_bucket_permission_dict=shared_bucket_user_permissions_dict,
        user_permissions_list=user_permissions_list,
    )

    with app.database_session() as session:
        with session.begin():
            workbench_activity = monitoring_models.WorkbenchActivity(
                id=uuid.uuid4(),
                workbench_id=workbench.id,
                workspace_id=workbench_renewal_request.workspace_project_id,
                invoker_email=workbench_renewal_request.user_email,
                build_type=enums.BuildType.WORKBENCH_UPDATE,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
            )
            session.add(workbench_activity)

            workflows.update_rstudio_workbench(
                build=build,
                workbench_activity_id=workbench_activity.id,
                user_email=workbench_renewal_request.user_email,
            )()

            return workbench_activity.id
