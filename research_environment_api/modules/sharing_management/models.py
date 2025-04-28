from datetime import datetime
from sqlalchemy import Enum, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from research_environment_api.modules.model import ScopedModel
from research_environment_api.modules.sharing_management.enums import SharingState, BucketPermissions, BucketRequestStatus


class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "sharing_"


class SharingData(Base):
    __local_tablename__ = "connections"

    sharer_email: Mapped[str] = mapped_column(String(), nullable=False)
    accessor_email: Mapped[str] = mapped_column(String(), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(), nullable=False)
    project_id: Mapped[str] = mapped_column(String(), nullable=False)
    state: Mapped[SharingState] = mapped_column(Enum(SharingState), nullable=False)


class BucketAccessRequest(Base):
    __local_tablename__ = "access_requests"

    requester_email: Mapped[str] = mapped_column(String(), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(), nullable=False)
    project_id: Mapped[str] = mapped_column(String(), nullable=False)
    requested_permissions: Mapped[BucketPermissions] = mapped_column(Enum(BucketPermissions), nullable=False)
    status: Mapped[BucketRequestStatus] = mapped_column(Enum(BucketRequestStatus), nullable=False, default=BucketRequestStatus.PENDING)
    sharer_email: Mapped[str] = mapped_column(String(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
