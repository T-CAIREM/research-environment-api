import random
import string
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable, Union

from research_environment_api.modules.workbench_management.entities import (
    Workbench,
    WorkbenchStatus,
    Region,
)
from research_environment_api.modules.sharing_management.entities import SharedBucket
from research_environment_api.background.enums import BuildType


GOOGLE_REGIONS_SHORTCUTS = {
    Region.US_CENTRAL.value: "us-c1",
    Region.EUROPE_WEST.value: "eu-w3",
    Region.NORTHAMERICA_NORTHEAST.value: "na-ne3",
    Region.AUSTRALIA_SOUTHEAST.value: "au-se1",
}


class WorkspaceStatus(StrEnum):
    CREATED = "created"
    CREATING = "creating"
    DESTROYING = "destroying"


WORKSPACE_ACTIVITY_TYPE_MAP = {
    BuildType.WORKSPACE_CREATION: WorkspaceStatus.CREATING,
    BuildType.WORKSPACE_DELETION: WorkspaceStatus.DESTROYING,
}


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
            f"{self.username[:15]}-{GOOGLE_REGIONS_SHORTCUTS[self.region.value]}-"
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
class SharedWorkspaceCreation:
    user_email: str
    workspace_project_id: str = field(init=False)
    billing_account_id: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.user_email.split("@")
        self.workspace_project_id = self._workspace_project_id()

    def _workspace_project_id(self):
        workspace_project_id = f"{self.username[:15]}-shared-" + "".join(
            random.choices(string.ascii_lowercase, k=5)
        )
        return workspace_project_id


@dataclass
class SharedWorkspaceDeletion:
    workspace_project_id: str
    user_email: str
    billing_account_id: str


@dataclass
class WorkspaceListQuery:
    email: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.email.split("@")


@dataclass
class SharedWorkspaceListQuery:
    email: str
    username: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.email.split("@")


@dataclass
class BillingInfo:
    billing_enabled: bool
    billing_account_id: str


@dataclass
class Workspace:
    gcp_project_id: str
    billing_info: BillingInfo
    region: str
    workbenches: Iterable[Workbench]
    status: WorkspaceStatus


@dataclass
class SharedWorkspace:
    gcp_project_id: str
    billing_info: BillingInfo
    buckets: Iterable[SharedBucket]
    status: WorkspaceStatus


@dataclass
class EntityScaffolding:
    id: str
    status: Union[WorkbenchStatus, WorkspaceStatus]
    gcp_project_id: str
