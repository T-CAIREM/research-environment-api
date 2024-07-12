from dataclasses import dataclass, field
from research_environment_api.modules.app import app

from google.cloud.iam_admin_v1.types import Role as GoogleRole


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


@dataclass
class UserGroupRoleListing:
    organization_id: str = field(init=False)

    def __post_init__(self):
        self.organization_id = app.config.organization_id


@dataclass
class UserGroupIAMListing(UserGroupRoleListing):
    group_name: str


@dataclass
class ChangeGroupRoles:
    group_name: str
    role_list: list[str]
    organization_id: str = field(init=False)

    def __post_init__(self):
        self.organization_id = app.config.organization_id


@dataclass
class RemoveRolesFromGroup:
    group_name: str
    role_list: list[str]
    organization_id: str = field(init=False)

    def __post_init__(self):
        self.organization_id = app.config.organization_id


@dataclass
class GoogleRole:
    full_name: str
    title: str
    description: str

    @classmethod
    def from_gcp_role(cls, role_instance: GoogleRole):
        return cls(
            full_name=role_instance.name,
            title=role_instance.title,
            description=role_instance.description,
        )
