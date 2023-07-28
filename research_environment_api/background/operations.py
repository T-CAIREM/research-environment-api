from abc import ABC, abstractmethod

import google.cloud.compute as compute
from google.api_core import operation

from research_environment_api.modules.app import app
from google.cloud.compute_v1 import Operation as CloudOperation
from research_environment_api.background.enums import ProcessStatus


class Operation(ABC):
    @abstractmethod
    def is_done(self):
        return False


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

    def status(self):
        operation = self._operation()
        if operation.error.errors:
            return ProcessStatus.FAILURE
        if operation.status == CloudOperation.Status.DONE:
            return ProcessStatus.SUCCESS
        return ProcessStatus.IN_PROGRESS

    def is_done(self):
        return self._operation().done

    def _operation(self) -> compute.Operation:
        client = app.config.google_zone_operations_client
        return client.get(project=self.project_id, zone=self.zone, operation=self.name)


class BuildOperation(Operation):
    def __init__(self, name: str):
        self.name = name

    def is_done(self):
        return self._operation().done

    def _operation(self) -> operation.Operation:
        client = app.config.google_operations_client
        return client.get_operation(name=self.name)
