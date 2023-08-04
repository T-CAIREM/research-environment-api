from enum import StrEnum


class BuildType(StrEnum):
    WORKSPACE_CREATION = "workspace_creation"
    WORKSPACE_DELETION = "workspace_deletion"
    JUPYTER_CREATION = "jupyter_creation"
    JUPYTER_DESTROY = "jupyter_destroy"
    RSTUDIO_CREATION = "rstudio_creation"
    JUPYTER_CREATION_RETRY = "jupyter_creation_retry"
    JUPYTER_STOP = "jupyter_stop"
    JUPYTER_START = "jupyter_start"
    JUPYTER_UPDATE = "jupyter_update"


class WorkflowStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FAILURE = "failure"
    SUCCESS = "success"


class OperationStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FAILURE = "failure"
    SUCCESS = "success"
