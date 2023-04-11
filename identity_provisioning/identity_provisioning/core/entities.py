import secrets
from typing import Self, Optional
from dataclasses import dataclass, field

from identity_provisioning import config

@dataclass
class GoogleWorkspaceUser:
    name: dict
    primary_email: str
    password: str
    change_password_at_next_login: bool = False

    @classmethod
    def from_platform_data(cls, user_name: str, family_name: str, given_name: str, password: str) -> Self:
        name = {
            "family_name": family_name,
            "given_name": given_name,
        }
        email = f"{user_name}@{config.ORGANIZATION_DOMAIN}"
        return cls(
            name=name,
            primary_email=email,
            password=password
        )


@dataclass
class CloudIdentity:
    email: str
    family_name: str
    given_name: str

    @classmethod
    def from_google_workspace_user(cls, google_workspace_user: GoogleWorkspaceUser):
        return cls(
            email=google_workspace_user.primary_email,
            family_name=google_workspace_user.name.get("family_name"),
            given_name=google_workspace_user.name.get("given_name")
        )


