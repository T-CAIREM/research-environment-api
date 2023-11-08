from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from research_environment_api.modules.model import ScopedModel
from research_environment_api.modules.sharing_management.enums import SharingState


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
