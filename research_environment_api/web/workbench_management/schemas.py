from marshmallow import Schema, fields

from research_environment_api.modules.workbench_management.entities import (
    GpuAcceleratorType,
    MachineType,
    Region,
    WorkbenchType,
)


class Workbench(Schema):
    workbench_type = fields.Enum(WorkbenchType, by_value=True, required=True)
    workspace_project_id = fields.Str(required=True)
    user_email = fields.Str(required=True)


class WorkbenchWithMetadata(Workbench):
    region = fields.Enum(Region, by_value=True, required=True)
    dataset_identifier = fields.Str(required=True)
    bucket_name = fields.Str(required=True)


class WorkbenchWithResources(WorkbenchWithMetadata):
    machine_type = fields.Enum(MachineType, by_value=True, required=True)
    disk_size = fields.Int(required=True)
    gpu_accelerator_type = fields.Enum(
        GpuAcceleratorType,
        by_value=True,
        allow_none=True,
    )


class WorkbenchCreateRequest(WorkbenchWithResources):
    pass


class WorkbenchToggleStateRequest(Workbench):
    workbench_resource_id = fields.Str(required=True)


class WorkbenchUpdateRequest(WorkbenchWithResources):
    workbench_resource_id = fields.Str(required=True)


class WorkbenchDestroyRequest(WorkbenchWithResources):
    workbench_resource_id = fields.Str(required=True)
