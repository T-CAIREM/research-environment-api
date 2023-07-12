from collections import namedtuple

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


ComputeEngineMachineResources = namedtuple(
    "ComputeEngineMachoneResources", ["cpu", "memory"]
)


MACHINE_TYPE_TO_RESOURCE_MAP = {
    "n1-standard-2": ComputeEngineMachineResources(2.0, 7.5),
    "n1-standard-4": ComputeEngineMachineResources(4.0, 15.0),
    "n1-standard-8": ComputeEngineMachineResources(8.0, 30.0),
    "n1-standard-16": ComputeEngineMachineResources(16.0, 60.0),
}
