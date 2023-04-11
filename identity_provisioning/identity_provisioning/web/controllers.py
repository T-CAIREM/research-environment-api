import marshmallow
from flask import request

from identity_provisioning.web import app, schemas
from identity_provisioning.core import services


@app.route("/create", methods=["POST"])
def create_cloud_identity():
    body = request.get_json()
    identity_provisioning_request_schema = schemas.IdentityProvisioningRequest()
    identity_provisioning_request = identity_provisioning_request_schema.load(body)

    provisioned_cloud_identity = services.provision_cloud_identity(identity_provisioning_request)
    provisioned_identity_schema = schemas.ProvisionedIdentity()
    serialized_cloud_identity = provisioned_identity_schema.dump(provisioned_cloud_identity)

    return serialized_cloud_identity, 201


@app.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422
