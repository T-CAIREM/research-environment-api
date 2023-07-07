from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column
from enum import EnumType

from research_environment_api.modules.db import ScopedModel
from research_environment_api.modules.workbench_management.enums import BuildType

from google.cloud.devtools.cloudbuild_v1 import Build

Status = Build.Status

class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workbench_"


class Workbench(Base):
    __local_tablename__ = "workbenches"

    gcp_identifier: Mapped[str] = mapped_column(String())


class WorkbenchActivity(Base):
    __local_tablename__ = "workbench_activities"

    gcp_build_identifier: Mapped[str] = mapped_column(String(), nullable=False)
    invoker_username: Mapped[str] = mapped_column(String(), nullable=False)
    build_type: Mapped[BuildType] = mapped_column(Enum(BuildType), nullable=False)
    build_status: Mapped[Build.Status] = mapped_column(Enum(Build.Status))
    build_error_information: Mapped[str] = mapped_column(String())
