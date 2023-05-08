from enum import StrEnum


class IamBillingRole(StrEnum):
    OWNER = "roles/billing.admin"
    SHARED_USER = "roles/billing.user"
