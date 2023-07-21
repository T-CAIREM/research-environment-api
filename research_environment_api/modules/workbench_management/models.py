from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild
from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from research_environment_api.modules.celery_management.enums import BuildType
from research_environment_api.modules.model import ScopedModel


class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workbench_"


class WorkbenchMetadata(Base):
    __local_tablename__ = "workbench_metadata"

    gcp_identifier: Mapped[str] = mapped_column(String())
    dataset_slug: Mapped[str] = mapped_column(String())
    dataset_version: Mapped[str] = mapped_column(String())
    zone: Mapped[str] = mapped_column(String())


class WorkbenchActivity(Base):
    __local_tablename__ = "workbench_activities"

    gcp_identifier: Mapped[str] = mapped_column(String(), nullable=False)
    invoker_email: Mapped[str] = mapped_column(String(), nullable=False)
    build_type: Mapped[BuildType] = mapped_column(Enum(BuildType), nullable=False)
    build_status: Mapped[CloudBuild.Status] = mapped_column(Enum(CloudBuild.Status), nullable=True)
    build_error_information: Mapped[str] = mapped_column(String(), nullable=True)
