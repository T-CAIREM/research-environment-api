from research_environment_api.modules.model import BaseModel


class CloudIdentity(BaseModel):
    primary_email = db.Column(db.String(256), unique=True)
    is_configured = db.Column(db.Boolean(), default=False)
