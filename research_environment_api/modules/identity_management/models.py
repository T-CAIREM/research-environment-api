import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID

from research_environment_api.modules.model import db


class CloudIdentity(db.Model):
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sqlalchemy.text("gen_random_uuid()"),
    )
    primary_email = db.Column(db.String(256), unique=True)
    is_configured = db.Column(db.Boolean(), default=False)
