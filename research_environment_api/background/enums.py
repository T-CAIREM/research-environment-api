from enum import StrEnum


class BuildType(StrEnum):
    WORKSPACE_CREATION = "workspace_creation"
    WORKSPACE_DELETION = "workspace_deletion"
    SHARED_WORKSPACE_CREATION = "shared_workspace_creation"
    SHARED_WORKSPACE_DELETION = "shared_workspace_deletion"
    WORKBENCH_CREATION = "workbench_creation"
    WORKBENCH_STOP = "workbench_stop"
    WORKBENCH_START = "workbench_start"
    WORKBENCH_UPDATE = "workbench_update"
    WORKBENCH_DESTROY = "workbench_destroy"


class WorkflowStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FAILURE = "failure"
    SUCCESS = "success"


class OperationStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FAILURE = "failure"
    SUCCESS = "success"


class InstanceType(StrEnum):
    JUPYTER = "jupyter"
    RSTUDIO = "rstudio"
    COLLABORATIVE = "collaborative"
