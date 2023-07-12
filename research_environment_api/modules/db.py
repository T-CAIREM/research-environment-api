import uuid

from sqlalchemy import create_engine, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.ext.declarative import declared_attr

from research_environment_api.modules.config import config


# FIXME: Create the engine in the top-level component of the application instead of when this module is imported.
engine = create_engine(config.database_url, echo=True)


def make_session() -> Session:
    return Session(engine)


class ScopedModel(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""

    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return cls.__table_prefix__ + cls.__local_tablename__

    id: Mapped[str] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
