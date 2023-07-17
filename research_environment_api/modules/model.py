import uuid

import sqlalchemy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ScopedModel(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""

    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return cls.__table_prefix__ + cls.__local_tablename__

    id: Mapped[str] = mapped_column(
        sqlalchemy.UUID(), primary_key=True, default=uuid.uuid4
    )
