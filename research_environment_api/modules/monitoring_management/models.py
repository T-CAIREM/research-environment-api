from datetime import datetime

from sqlalchemy import Enum, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from research_environment_api.background.enums import (
    BuildType,
    WorkflowStatus,
    InstanceType,
)
from research_environment_api.modules.model import ScopedModel


class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workbench_"


class WorkbenchActivity(Base):
    __local_tablename__ = "workbench_activities"

    invoker_email: Mapped[str] = mapped_column(String(), nullable=False)
    workbench_id: Mapped[str] = mapped_column(String(), nullable=True)
    build_type: Mapped[BuildType] = mapped_column(Enum(BuildType), nullable=False)
    build_status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), nullable=True
    )
    workspace_id: Mapped[str] = mapped_column(String(), nullable=False)
    build_error_information: Mapped[str] = mapped_column(String(), nullable=True)


class WorkbenchMonitoringData(Base):
    __local_tablename__ = "monitoring_data"

    user_email: Mapped[str] = mapped_column(String(), nullable=False)
    dataset_identifier: Mapped[str] = mapped_column(String(), nullable=True)
    instance_type: Mapped[InstanceType] = mapped_column(
        Enum(InstanceType), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    workbench_id: Mapped[str] = mapped_column(String(), nullable=True)
