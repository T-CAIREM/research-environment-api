import random
import string
from dataclasses import dataclass, field
from typing import List

from research_environment_api.modules.workbench_management.entities import Workbench
from research_environment_api.modules.workspace_management.constants import (
    GOOGLE_REGIONS_SHORTCUTS,
)
from research_environment_api.modules.workspace_management.enums import Region


@dataclass
class WorkspaceCreation:
    region: Region
    user_email: str
    workspace_project_id: str = field(init=False)
    billing_account_id: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.user_email.split("@")
        self.workspace_project_id = self._workspace_project_id()

    def _workspace_project_id(self):
        workspace_project_id = (
            f"{self.username[:15]}-{GOOGLE_REGIONS_SHORTCUTS[self.region]}-"
            + "".join(random.choices(string.ascii_lowercase, k=5))
        )
        return workspace_project_id


@dataclass
class WorkspaceDeletion:
    workspace_project_id: str
    region: Region
    user_email: str
    billing_account_id: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.user_email.split("@")


@dataclass
class WorkspaceListQuery:
    email: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.email.split("@")


@dataclass
class Workspace:
    gcp_project_id: str
    billing_account_id: str
    region: str
    workbenches: List[Workbench]
