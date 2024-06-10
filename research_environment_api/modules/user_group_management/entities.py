from dataclasses import dataclass, field
from research_environment_api.modules.app import app


@dataclass
class UserGroupCreation:
    group_name: str
    description: str
    customer_id: str = field(init=False)

    def __post_init__(self):
        self.customer_id = app.config.customer_id


@dataclass
class UserGroupDeletion:
    group_name: str
