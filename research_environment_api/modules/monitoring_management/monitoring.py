from typing import Iterable

from sqlalchemy import func

from research_environment_api.background import enums
from research_environment_api.modules.app import app
from research_environment_api.modules.monitoring_management import models


def list_active_workflows(user_email: str) -> Iterable[models.WorkbenchActivity]:
    with app.database_session() as session:
        workbench_activities = (
            session.query(models.WorkbenchActivity)
            .filter_by(
                invoker_email=user_email, build_status=enums.WorkflowStatus.IN_PROGRESS
            )
            .all()
        )
    return workbench_activities


def get_workflow(workflow_id: str) -> models.WorkbenchActivity:
    with app.database_session() as session:
        workbench_activity = (
            session.query(models.WorkbenchActivity).filter_by(id=workflow_id).one()
        )
    return workbench_activity


def list_workbench_monitoring_data_entries() -> (
    Iterable[models.WorkbenchMonitoringData]
):
    with app.database_session() as session:
        workbench_monitoring_data_entries = session.query(
            models.WorkbenchMonitoringData
        ).all()

    return workbench_monitoring_data_entries


def get_active_users_per_dataset() -> (
    Iterable[models.WorkbenchMonitoringData]
):
    with app.database_session() as session:
        active_users_per_dataset_entries = (
            session.query(
                models.WorkbenchMonitoringData.dataset_identifier,
                func.array_agg(models.WorkbenchMonitoringData.user_email).label(
                    "user_emails"
                ),
            )
            .filter(models.WorkbenchMonitoringData.deleted_at.is_(None))
            .group_by(models.WorkbenchMonitoringData.dataset_identifier)
            .all()
        )

    return active_users_per_dataset_entries
