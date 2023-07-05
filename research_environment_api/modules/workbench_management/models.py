from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from research_environment_api.modules.db import ScopedModel


class Base(ScopedModel):
    __abstract__ = True
    __table_prefix__ = "workbench_"


class Workbench(Base):
    __local_tablename__ = "workbenches"

    gcp_identifier: Mapped[str] = mapped_column(String())
