from sqlalchemy import Enum, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum as PyEnum

from research_environment_api.modules.model import ScopedModel


class CollaboratorStatus(PyEnum):
    SUCCESS = "success"
    FAILED = "failed"


class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workbench_"


class WorkbenchCollaboratorData(Base):
    __local_tablename__ = "collaborators"

    workspace_project_id: Mapped[str] = mapped_column(String(), nullable=False)
    service_account_name: Mapped[str] = mapped_column(String(), nullable=False)
    collaborator_email: Mapped[str] = mapped_column(String(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    viewed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[CollaboratorStatus] = mapped_column(
        Enum(CollaboratorStatus), nullable=False
    )
