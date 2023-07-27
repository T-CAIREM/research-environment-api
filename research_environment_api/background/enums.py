from enum import StrEnum


class BuildType(StrEnum):
    WORKSPACE_CREATION = "workspace_creation"
    WORKSPACE_DELETION = "workspace_deletion"
    JUPYTER_CREATION = "jupyter_creation"
    RSTUDIO_CREATION = "rstudio_creation"
    JUPYTER_CREATION_RETRY = "jupyter_creation_retry"
    JUPYTER_STOP = "jupyter_stop"
