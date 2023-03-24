from typing import Self, Optional
from dataclasses import dataclass, field

import config
import enums


@dataclass(frozen=True)
class CloudIdentity:
    email: str
    family_name: str
    given_name: str
    provisioning_status: enums.CloudIdentityProvisioningStatus

    @classmethod
    def from_platform_data(
        cls, user_name: str, family_name: str, given_name: str
    ) -> Self:
        email = f"{user_name}@{config.ORGANIZATION_DOMAIN}"
        initial_status = enums.CloudIdentityProvisioningStatus.INITIAL
        return cls(
            email=email,
            family_name=family_name,
            given_name=given_name,
            provisioning_status=initial_status,
        )

    @property
    def is_provisioned(self) -> bool:
        return (
            self.provisioning_status
            == enums.CloudIdentityProvisioningStatus.PROVISIONED
        )

    @property
    def is_created_in_workspace(self) -> bool:
        return (
            self.provisioning_status
            == enums.CloudIdentityProvisioningStatus.CREATED_IN_WORKSPACE
        )

    @property
    def is_initial(self) -> bool:
        return self.provisioning_status == enums.CloudIdentityProvisioningStatus.INITIAL


@dataclass(frozen=True)
class GoogleWorkspaceUser:
    name: dict
    primary_email: str
    password: str = field(init=False)
    change_password_at_next_login: bool = True

    def __post_init__(self):
        self.password = self.generate_password()

    @classmethod
    def from_cloud_identity(cls, cloud_identity: CloudIdentity) -> Self:
        return cls(**cloud_identity)

    @staticmethod
    def generate_password() -> str:
        return secrets.token_urlsafe(config.DEFAULT_PASSWORD_LENGTH)
