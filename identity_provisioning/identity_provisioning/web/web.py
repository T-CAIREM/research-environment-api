from flask import Flask

from identity_provisioning.web import schemas
from identity_provisioning import core

app = Flask(__name__)


@app.route("/", methods=["POST"])
def entrypoint():
    body = request.get_json()
    cloud_identity_creation_schema = schemas.CloudIdentityCreation()
    new_cloud_identity = cloud_identity_schema.load(**body)

    core.services.provision_cloud_identity(new_cloud_identity)

    return cloud_identity_schema.dump(cloud_identity), 201
