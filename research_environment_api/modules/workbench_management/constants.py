from collections import namedtuple


AVAILABLE_ZONES = {
    "us-central": ["a", "b", "c", "f"],
    "northamerica-northeast1": ["a", "b", "c"],
    "europe-west3": ["a", "b", "c"],
    "australia-southeast1": ["a", "b", "c"],
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
