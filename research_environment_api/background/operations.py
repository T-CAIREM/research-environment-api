from abc import ABC, abstractmethod

import google.cloud.compute as compute
from google.api_core import operation

from research_environment_api.background.enums import OperationStatus
from research_environment_api.modules.app import app


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
        if not operation.done:
            return OperationStatus.IN_PROGRESS

        return OperationStatus.FAILURE if operation.error else OperationStatus.SUCCESS

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
        if not operation.done:
            return OperationStatus.IN_PROGRESS

        return (
            OperationStatus.FAILURE if operation.error.code else OperationStatus.SUCCESS
        )

    def is_done(self) -> bool:
        return self._operation().done

    def _operation(self) -> operation.Operation:
        client = app.config.google_operations_client
        return client.get_operation(name=self.name)
