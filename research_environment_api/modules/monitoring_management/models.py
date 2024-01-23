from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from research_environment_api.background.enums import BuildType, WorkflowStatus
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
