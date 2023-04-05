import secrets
from typing import Self, Optional
from dataclasses import dataclass, field

from identity_provisioning import config


@dataclass
class CloudIdentity:
    email: str
    family_name: str
    given_name: str

    @classmethod
    def from_platform_data(
        cls, user_name: str, family_name: str, given_name: str
    ) -> Self:
        email = f"{user_name}@{config.ORGANIZATION_DOMAIN}"
        return cls(
            email=email,
            family_name=family_name,
            given_name=given_name,
        )


@dataclass
class GoogleWorkspaceUser:
    name: dict
    primary_email: str
    password: str
    change_password_at_next_login: bool = False

    @classmethod
    def from_cloud_identity(cls, cloud_identity: CloudIdentity, password: str) -> Self:
        name = {
            "family_name": cloud_identity.family_name,
            "given_name": cloud_identity.given_name,
        }
        primary_email = cloud_identity.email
        return cls(name=name, primary_email=primary_email, password=password)
