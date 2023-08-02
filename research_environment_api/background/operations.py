from abc import ABC, abstractmethod

import google.cloud.compute as compute
from google.api_core import operation

from research_environment_api.modules.app import app
from google.cloud.compute_v1 import Operation as CloudOperation
from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild
from research_environment_api.background.enums import OperationStatus


CLOUD_BUILD_OPERATION_STATUS_MAP = {
    CloudBuild.Status.PENDING: OperationStatus.IN_PROGRESS,
    CloudBuild.Status.QUEUED: OperationStatus.IN_PROGRESS,
    CloudBuild.Status.WORKING: OperationStatus.IN_PROGRESS,
    CloudBuild.Status.SUCCESS: OperationStatus.SUCCESS,
    CloudBuild.Status.FAILURE: OperationStatus.FAILURE,
    CloudBuild.Status.INTERNAL_ERROR: OperationStatus.FAILURE,
    CloudBuild.Status.TIMEOUT: OperationStatus.FAILURE,
    CloudBuild.Status.CANCELLED: OperationStatus.FAILURE,
    CloudBuild.Status.EXPIRED: OperationStatus.FAILURE,
    CloudBuild.Status.STATUS_UNKNOWN: OperationStatus.FAILURE,
}


class Operation(ABC):
    @abstractmethod
    def is_done(self) -> bool:
        return False

    @abstractmethod
    def status(self) -> OperationStatus:
        return OperationStatus.FAILURE


class InstanceOperation(Operation):
    def __init__(
        self,
        project_id: str,
        zone: str,
        name: str,
    ):
        self.project_id = project_id
        self.zone = zone
        self.name = name

    def status(self) -> OperationStatus:
        operation = self._operation()
        if operation.status != CloudOperation.Status.DONE:
            return OperationStatus.IN_PROGRESS

        return (
            OperationStatus.FAILURE
            if operation.error.errors
            else OperationStatus.SUCCESS
        )

    def is_done(self) -> bool:
        return self._operation().done

    def _operation(self) -> compute.Operation:
        client = app.config.google_zone_operations_client
        return client.get(project=self.project_id, zone=self.zone, operation=self.name)


class BuildOperation(Operation):
    def __init__(self, name: str):
        self.name = name

    def status(self) -> OperationStatus:
        operation = self._operation()

        return CLOUD_BUILD_OPERATION_STATUS_MAP[operation.status]

    def is_done(self) -> bool:
        return self._operation().done

    def _operation(self) -> operation.Operation:
        client = app.config.google_operations_client
        return client.get_operation(name=self.name)
