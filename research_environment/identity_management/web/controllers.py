import marshmallow
from flask import request

from research_environment.identity_management.web import (
    identity_management_bp,
    schemas,
)
from research_environment.identity_management.core import services


@identity_management_bp.route("/identity/<identity_id>", methods=["GET"])
def fetch_cloud_identity(identity_id):
    cloud_identity = services.fetch_cloud_identity(identity_id)
    cloud_identity_schema = schemas.CloudIdentity()
    serialized_cloud_identity = cloud_identity_schema.dump(cloud_identity)

    return serialized_cloud_identity, 201


@identity_management_bp.route("/identity/create", methods=["POST"])
def create_cloud_identity():
    body = request.get_json()
    identity_provisioning_request_schema = schemas.IdentityProvisioningRequest()
    identity_provisioning_request = identity_provisioning_request_schema.load(body)

    provisioned_cloud_identity = services.provision_cloud_identity(
        identity_provisioning_request
    )
    provisioned_identity_schema = schemas.ProvisionedIdentity()
    serialized_cloud_identity = provisioned_identity_schema.dump(
        provisioned_cloud_identity
    )

    return serialized_cloud_identity, 201


@identity_management_bp.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422
