from enum import StrEnum


class BillingAccountRole(StrEnum):
    OWNER = "owner"
    SHARED_USER = "shared_user"
