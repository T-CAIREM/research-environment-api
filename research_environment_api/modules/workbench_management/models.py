from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild
from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column

from research_environment_api.modules.db import ScopedModel
from research_environment_api.modules.workbench_management.enums import BuildType


class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workbench_"


class WorkbenchMetadata(Base):
    __local_tablename__ = "workbench_metadata"

    gcp_identifier: Mapped[str] = mapped_column(String())
    dataset_slug: Mapped[str] = mapped_column(String())
    dataset_version: Mapped[str] = mapped_column(String())


class WorkbenchActivity(Base):
    __local_tablename__ = "workbench_activities"

    gcp_build_identifier: Mapped[str] = mapped_column(String(), nullable=False)
    invoker_username: Mapped[str] = mapped_column(String(), nullable=False)
    build_type: Mapped[BuildType] = mapped_column(Enum(BuildType), nullable=False)
    build_status: Mapped[CloudBuild.Status] = mapped_column(Enum(CloudBuild.Status))
    build_error_information: Mapped[str] = mapped_column(String())
