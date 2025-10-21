from collections import namedtuple
from enum import Enum as StrEnum

from google.iam.v1 import policy_pb2
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
            machine_type_to_resource_map[
                machine_type_name
            ] = ComputeEngineMachineResources(
                machine_type.guest_cpus,
                machine_type.memory_mb / 1024,
            )
    return machine_type_to_resource_map, machine_type_enum


def format_gpu_accelerator_type(gpu_accelerator_type: str) -> str:
    """
    Converts a GPU accelerator type from Google format (e.g., 'nvidia-tesla-k80')
    to Vertex AI format (e.g., 'NVIDIA_TESLA_K80').
    """
    if not gpu_accelerator_type:
        return ""
    return gpu_accelerator_type.upper().replace("-", "_")


def format_service_account_resource(
    workspace_project_id: str, service_account_name: str
) -> str:
    """Format the service account resource string for IAM operations."""
    return f"projects/{workspace_project_id}/serviceAccounts/{service_account_name}@{workspace_project_id}.iam.gserviceaccount.com"


def add_iam_binding(iam_client, resource: str, user_email: str, role: str):
    """
    Adds IAM binding for a user to a resource with the specified role.
    Returns True if binding was added, False if user already had access.
    """
    user_member = f"user:{user_email}"
    policy = iam_client.get_iam_policy(request={"resource": resource})
    bindings = policy.bindings

    role_binding = next((b for b in bindings if b.role == role), None)

    if role_binding:
        if user_member in role_binding.members:
            return False
        role_binding.members.append(user_member)
    else:
        bindings.append(policy_pb2.Binding(role=role, members=[user_member]))

    updated_policy = policy_pb2.Policy(bindings=bindings)
    iam_client.set_iam_policy(request={"resource": resource, "policy": updated_policy})
    return True


def remove_iam_binding(iam_client, resource: str, user_email: str, role: str):
    """
    Removes IAM binding for a user from a resource with the specified role.
    Returns True if binding was removed, False if user didn't have access.
    """
    user_member = f"user:{user_email}"

    policy = iam_client.get_iam_policy(request={"resource": resource})
    bindings = policy.bindings

    role_binding = next((b for b in bindings if b.role == role), None)

    if not role_binding or user_member not in role_binding.members:
        return False

    role_binding.members.remove(user_member)
    updated_policy = policy_pb2.Policy(bindings=bindings)
    iam_client.set_iam_policy(request={"resource": resource, "policy": updated_policy})
    return True
