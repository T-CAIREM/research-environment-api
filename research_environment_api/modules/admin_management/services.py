from typing import Iterable

from research_environment_api.modules.monitoring_management import monitoring
from research_environment_api.modules.workbench_management.services import (
    list_workbenches,
)
from research_environment_api.modules.workspace_management.services import (
    _list_all_active_google_projects,
)
from research_environment_api.modules.workbench_management.entities import (
    Workbench,
    WorkbenchDestroy,
    WorkbenchToggleState,
    WorkbenchType,
)
from research_environment_api.background import schedulers


def get_event_workbenches() -> Iterable:
    gcp_projects = _list_all_active_google_projects()

    project_ids = {project.project_id for project in gcp_projects}

    workflows_in_progress = monitoring.list_all_active_workflows()

    all_workbenches = [
        (gcp_project_id, wb)
        for gcp_project_id in project_ids
        for wb in list_workbenches(
            gcp_project_id=gcp_project_id,
            workflows_in_progress=workflows_in_progress,
        )
        if getattr(wb, "associated_event", None)
    ]

    return all_workbenches


def destroy_event_workbenches(
    workbenches_with_events: Iterable[tuple[str, Workbench]], event_slug: str
):
    for gcp_project_id, workbench in workbenches_with_events:
        if workbench.associated_event == event_slug:
            user_email = f"{workbench.workbench_owner_username}@healthdatanexus.ai"
            workbench_destroy_entity = WorkbenchDestroy(
                workbench_type=workbench.type,
                workspace_project_id=gcp_project_id,
                user_email=user_email,
                workbench_resource_id=workbench.id,
            )
            workbench_type = workbench.type
            if workbench_type == WorkbenchType.JUPYTER:
                schedulers.destroy_jupyter_workbench_flow(
                    workbench_destroy_entity, workbench
                )
            elif workbench_type == WorkbenchType.COLLABORATIVE:
                schedulers.destroy_collaborative_workbench_flow(
                    workbench_destroy_entity, workbench
                )
            elif workbench_type == WorkbenchType.RSTUDIO:
                schedulers.destroy_rstudio_workbench_flow(
                    workbench_destroy_entity, workbench
                )


def stop_event_workbenches(workbenches_with_events: Iterable[tuple[str, Workbench]], event_slug: str):
    for gcp_project_id, workbench in workbenches_with_events:
        if workbench.associated_event == event_slug:
            user_email = f"{workbench.workbench_owner_username}@healthdatanexus.ai"
            workbench_stop_entity = WorkbenchToggleState(
                workbench_type=workbench.type,
                workspace_project_id=gcp_project_id,
                user_email=user_email,
                workbench_resource_id=workbench.id,
            )
            workbench_type = workbench.type
            if workbench_type == WorkbenchType.JUPYTER:
                schedulers.stop_jupyter_workbench(
                    workbench_stop_entity
                )
            elif workbench_type == WorkbenchType.COLLABORATIVE:
                schedulers.stop_collaborative_workbench(workbench_stop_entity)
            elif workbench_type == WorkbenchType.RSTUDIO:
                schedulers.stop_compute_engine_workbench(workbench_stop_entity)
