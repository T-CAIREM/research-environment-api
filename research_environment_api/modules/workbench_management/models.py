from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, Enum

from research_environment_api.modules.db import ScopedModel
from research_environment_api.modules.workbench_management.enums import BuildType

from google.cloud.devtools.cloudbuild_v1 import Build


class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workbench_"


class Workbench(Base):
    __local_tablename__ = "workbenches"

    gcp_identifier: Mapped[str] = mapped_column(String())


class WorkbenchActivity(Base):
    __local_tablename__ = "workbench_activities"

    gcp_build_identifier: Mapped[str] = mapped_column(String(), nullable=False)
    build_type: Mapped[Enum] = mapped_column(Enum(BuildType), nullable=False)
    build_status = Mapped[Enum] = mapped_column(Enum(Build.Status))
