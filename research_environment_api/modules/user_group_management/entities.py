from dataclasses import dataclass, field
from research_environment_api.modules.app import app


@dataclass
class UserGroupCreation:
    group_name: str
    description: str
    organization_id: str = field(init=False)

    def __post_init__(self):
        self.organization_id = app.config.organization_id


@dataclass
class GetUserPermissions:
    groups: str
    organization_id: str
