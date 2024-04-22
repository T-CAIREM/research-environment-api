from flask import request

from research_environment_api.modules.identity_management import entities, services
from research_environment_api.web.decorators import validate_token
from research_environment_api.web.identity_management import (
    identity_management_bp,
    schemas,
)


@identity_management_bp.post("/create")
@validate_token
def create_cloud_identity():
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
    body = request.get_json()
    identity_provisioning_request = schemas.IdentityProvisioningRequest().load(body)
    cloud_identity_creation_entity = entities.CloudIdentityCreation(
        **identity_provisioning_request
    )

    provisioned_cloud_identity = services.provision_cloud_identity(
        cloud_identity_creation_entity
    )
    serialized_cloud_identity = schemas.ProvisionedIdentity().dump(
        provisioned_cloud_identity
    )

    return serialized_cloud_identity, 201
