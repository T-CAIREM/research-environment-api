from flask import request

from research_environment_api.modules.monitoring_management import services
from research_environment_api.web.decorators import validate_token
from research_environment_api.web.monitoring_management import (
    monitoring_management_bp,
    schemas,
)


@monitoring_management_bp.get("/datasets")
@validate_token
def list_workbench_monitoring_data_entries():
    """Creates a cloud identity.
    ---
    post:
      tags:
        - identity_management
      description: Creates a cloud identity.
      requestBody:
        content:
          application/json:
            schema: IdentityProvisioningRequest
      responses:
        200:
          description: Returns the created cloud identity.
          content:
            application/json:
              schema: ProvisionedIdentity
    """

    workbenches_monitoring_data_entries = (
        services.list_workbench_monitoring_data_entries()
    )
    serialized_workbenches_monitoring_data = schemas.WorkbenchMonitoringDataEntry(
        many=True
    ).dump(workbenches_monitoring_data_entries)

    return serialized_workbenches_monitoring_data, 200
