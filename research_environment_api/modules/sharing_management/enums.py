from enum import StrEnum


class IamSharingRole(StrEnum):
    ADMIN = "roles/storage.admin"
    USER = "roles/storage.objectViewer"


class SharedBucketRole(StrEnum):
    OWNER = "owner"
    SHARED_USER = "shared_user"


class SharingState(StrEnum):
    SHARED = "shared"
    REVOKED = "revoked"


class BucketPermissions(StrEnum):
    READ_WRITE = "read_write"
    READ = "read"
