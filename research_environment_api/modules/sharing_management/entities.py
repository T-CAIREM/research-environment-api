import random
import string
from dataclasses import dataclass, field

from research_environment_api.modules.workbench_management.entities import (
    Region,
)

from google.cloud.storage import Bucket as GCPBucket


@dataclass
class SharedBucketCreation:
    region: Region
    workspace_project_id: str
    user_email: str
    storage_class: str = "STANDARD"
    username: str = field(init=False)
    bucket_name: str = field(init=False)

    def __post_init__(self):
        self.username, domain = self.user_email.split("@")
        self.bucket_name = self._bucket_name()

    def _bucket_name(self):
        bucket_name = f"{self.username[:15]}-{self.region}-shared-bucket-" + "".join(
            random.choices(string.ascii_lowercase, k=5)
        )
        return bucket_name


@dataclass
class SharedBucketDeletion:
    bucket_name: str


@dataclass
class ShareBucket:
    sharer_email: str
    accessor_email: str
    bucket_name: str
    project_id: str


@dataclass
class SharedBucket:
    bucket_name: str
    is_owner: bool

    @classmethod
    def from_storage_instance(
        cls,
        instance: GCPBucket,
        username: str,
    ):
        is_owner = bool(instance.labels["cloud_identity_username"] == username)
        return cls(
            bucket_name=instance.name,
            is_owner=is_owner,
        )


@dataclass
class RevokeSharedBucketAccess:
    sharer_email: str
    accessor_email: str
    bucket_name: str


@dataclass
class GenerateSignedUrl:
    filename: str
    size: int
    bucket_name: str
