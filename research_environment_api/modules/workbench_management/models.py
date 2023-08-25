from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from research_environment_api.background.enums import BuildType, WorkflowStatus
from research_environment_api.modules.model import ScopedModel


class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workbench_"


class AppEngineMetadata(Base):
    __local_tablename__ = "app_engine_metadata"

    instance_id: Mapped[str] = mapped_column(String(), nullable=False)
    dataset_identifier: Mapped[str] = mapped_column(String(), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(), nullable=False)
    vm_image: Mapped[str] = mapped_column(String(), nullable=False)
    region: Mapped[str] = mapped_column(String(), nullable=False)
    disk_size: Mapped[str] = mapped_column(String(), nullable=False)
    machine_type: Mapped[str] = mapped_column(String(), nullable=False)


class WorkbenchActivity(Base):
    __local_tablename__ = "workbench_activities"

    invoker_email: Mapped[str] = mapped_column(String(), nullable=False)
    build_type: Mapped[BuildType] = mapped_column(Enum(BuildType), nullable=False)
    build_status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), nullable=True
    )
    build_error_information: Mapped[str] = mapped_column(String(), nullable=True)
