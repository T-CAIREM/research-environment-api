import marshmallow
from flask import request

from identity_provisioning.web import app, schemas
from identity_provisioning.core import services


@app.route("/create", methods=["POST"])
def create_cloud_identity():
    body = request.get_json()
    cloud_identity_creation_schema = schemas.CloudIdentityCreation()
    cloud_identity = cloud_identity_creation_schema.load(body)

    provisioned_cloud_identity = services.provision_cloud_identity(cloud_identity)
    cloud_identity_schema = schemas.CloudIdentity()
    serialized_cloud_identity = cloud_identity_schema.dump(provisioned_cloud_identity)

    return serialized_cloud_identity, 201


@app.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422
