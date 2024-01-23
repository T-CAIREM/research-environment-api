import random
import string
from dataclasses import dataclass, field

from research_environment_api.modules.workbench_management.entities import (
    Region,
)


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
