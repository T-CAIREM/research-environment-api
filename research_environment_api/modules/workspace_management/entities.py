from dataclasses import dataclass, field
from research_environment_api.modules.workspace_management.constants import GOOGLE_REGIONS_SHORTCUTS
import random
import string


@dataclass
class GoogleWorkspaceCreation:
    region: str
    email: str
    project_name: str = field(init=False)
    billing_account_id: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.email.split("@")
        self.project_name = (
            f"{self.username[:15]}-{GOOGLE_REGIONS_SHORTCUTS[self.region]}-"
            + ''.join(random.choices(string.ascii_letters, k=5))
        )


@dataclass
class GoogleWorkspaceListing:
    username: str
