from dataclasses import dataclass, field
from enums import Region
from constants import GOOGLE_REGIONS_SHORTCUTS
import random
import string


@dataclass
class GoogleWorkspaceCreation:
    region: Region
    family_name: str
    project_name: field(init=False)
    billing_account_resource_name: str

    def __post_init__(self):
        self.project_name = (
            f"{self.family_name[:15]}-{GOOGLE_REGIONS_SHORTCUTS[self.region]}-"
            + ''.join(random.choices(string.ascii_letters, k=5))
        )


@dataclass
class GoogleWorkspaceListing:
    family_name: str
