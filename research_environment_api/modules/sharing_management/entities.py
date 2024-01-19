import random
import string
import datetime
from dataclasses import dataclass, field
from typing import Self
from enum import StrEnum

from research_environment_api.modules.workbench_management.entities import (
    Region,
)

from google.cloud.storage import Bucket as GCPBucket


class BucketObjectType(StrEnum):
    DIRECTORY = "directory"
    FILE = "file"


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
    ) -> Self:
        is_owner = instance.labels["cloud_identity_username"] == username
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


@dataclass
class GetSharedBucketContent:
    bucket_name: str
    subdir: str


@dataclass
class DeleteSharedBucketContent:
    bucket_name: str
    full_path: str


@dataclass
class CreateSharedBucketDirectory:
    bucket_name: str
    parent_path: str
    directory_name: str
    directory_path: str = field(init=False)

    def __post_init__(self):
        self.directory_path = self.parent_path + self.directory_name + "/"


@dataclass
class SharedBucketObject:
    type: BucketObjectType
    name: str
    full_path: str
    size: str = None
    modification_time: str = None
