from enum import StrEnum


class BuildType(StrEnum):
    JUPYTER_CREATION = "jupyter_creation"
    RSTUDIO_CREATION = "rstudio_creation"
    JUPYTER_CREATION_RETRY = "jupyter_creation_retry"
    JUPYTER_STOP = "jupyter_stop"
    JUPYTER_UPDATE = "jupyter_update"
