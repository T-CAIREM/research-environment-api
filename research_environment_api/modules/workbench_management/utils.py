from collections import namedtuple
from enum import Enum as StrEnum

from google.cloud.compute_v1.types.compute import AggregatedListMachineTypesRequest
from google.cloud import compute_v1

ComputeEngineMachineResources = namedtuple(
    "ComputeEngineMachoneResources", ["cpu", "memory"]
)


def generate_machine_types(page_result, zones):
    machine_types_dict = {}
    for zone in zones:
        machine_types = page_result.items[zone]
        for machine_type in machine_types.machine_types:
            machine_type_name = machine_type.name.split("/")[-1]
            machine_type_enum_name = machine_type_name.upper().replace("-", "_")
            if machine_type_enum_name not in machine_types_dict.keys():
                machine_types_dict[machine_type_enum_name] = machine_type_name

    return StrEnum("MachineType", machine_types_dict)

def generate_required_maps(project_id: str):
    machine_type_to_resource_map = {}
    compute_client = compute_v1.MachineTypesClient()
    machine_types_request = AggregatedListMachineTypesRequest(project=project_id)
    page_result = compute_client.aggregated_list(machine_types_request)
    zones = [zone for zone in page_result.items]
    machine_type_enum = generate_machine_types(page_result, zones)
    for zone in page_result.items:
        machine_types = page_result.items[zone]
        for machine_type in machine_types.machine_types:
            machine_type_name = machine_type.name.split("/")[-1]
            machine_type_to_resource_map[machine_type_name] = ComputeEngineMachineResources(
                machine_type.guest_cpus,
                machine_type.memory_mb / 1024,
            )
    return machine_type_to_resource_map, machine_type_enum


