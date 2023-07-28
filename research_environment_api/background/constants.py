from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild
from google.cloud.compute_v1 import Operation
from research_environment_api.background.enums import ProcessStatus

AVAILABLE_ZONES = {
    "us-central1": ["us-central1-a", "us-central1-b", "us-central1-c", "us-central1-f"],
    "northamerica-northeast1": [
        "northamerica-northeast1-a",
        "northamerica-northeast1-b",
        "northamerica-northeast1-c",
    ],
    "europe-west3": ["europe-west3-a", "europe-west3-b", "europe-west3-c"],
    "australia-southeast1": [
        "australia-southeast1-a",
        "australia-southeast1-b",
        "australia-southeast1-c",
    ],
}

CLOUD_BUILD_ERROR_MESSAGE = {14: "insufficient resources"}


CLOUD_BUILD_STATUS_MAP = {
    CloudBuild.Status.PENDING: ProcessStatus.IN_PROGRESS,
    CloudBuild.Status.QUEUED: ProcessStatus.IN_PROGRESS,
    CloudBuild.Status.WORKING: ProcessStatus.IN_PROGRESS,
    CloudBuild.Status.SUCCESS: ProcessStatus.SUCCESS,
    CloudBuild.Status.FAILURE: ProcessStatus.FAILURE,
    CloudBuild.Status.INTERNAL_ERROR: ProcessStatus.FAILURE,
    CloudBuild.Status.TIMEOUT: ProcessStatus.FAILURE,
    CloudBuild.Status.CANCELLED: ProcessStatus.FAILURE,
    CloudBuild.Status.EXPIRED: ProcessStatus.FAILURE,
    CloudBuild.Status.STATUS_UNKNOWN: ProcessStatus.FAILURE,
}

INSTANCE_STATUS_MAP = {
    Operation.Status.PENDING: ProcessStatus.IN_PROGRESS,
    Operation.Status.RUNNING: ProcessStatus.IN_PROGRESS,
    Operation.Status.UNDEFINED_STATUS: ProcessStatus.FAILURE,
}
