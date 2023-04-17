import secrets
from typing import Self, Optional
from dataclasses import dataclass, field

from research_environment_api.modules.identity_management import config


@dataclass
class CloudIdentity:
    email: str
    password: str
    recovery_email: str
    family_name: str
    given_name: str

    @classmethod
    def from_platform_data(
        cls,
        user_name: str,
        password: str,
        recovery_email: str,
        family_name: str,
        given_name: str,
    ) -> Self:
        email = f"{user_name}@{config.ORGANIZATION_DOMAIN}"
        return cls(
            email=email,
            password=password,
            recovery_email=recovery_email,
            family_name=family_name,
            given_name=given_name,
        )


@dataclass
class GoogleWorkspaceUser:
    name: dict
    primary_email: str
    recovery_email: str
    password: str
    change_password_at_next_login: bool = False

    @classmethod
    def from_cloud_identity(cls, cloud_identity: CloudIdentity) -> Self:
        name = {
            "family_name": cloud_identity.family_name,
            "given_name": cloud_identity.given_name,
        }
        return cls(
            name=name,
            primary_email=cloud_identity.email,
            recovery_email=cloud_identity.recovery_email,
            password=cloud_identity.password,
        )


@dataclass
class StoredCloudIdentityData:
    email: str
    recovery_email: str
    family_name: str
    given_name: str

    @classmethod
    def from_cloud_identity(cls, cloud_identity: CloudIdentity) -> Self:
        return cls(
            email=cloud_identity.email,
            recovery_email=cloud_identity.recovery_email,
            family_name=cloud_identity.family_name,
            given_name=cloud_identity.given_name,
        )
