from enum import StrEnum, auto


class CloudIdentityProvisioningStatus(StrEnum):
    INITIAL = auto()
    CREATED_IN_WORKSPACE = auto()
    PROVISIONED = auto()
