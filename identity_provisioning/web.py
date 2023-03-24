from flask import Flask

import schemas
import enums
import services

app = Flask(__name__)


@app.route("/", methods=["POST"])
def entrypoint():
    body = request.get_json()
    cloud_identity_creation_schema = schemas.CloudIdentityCreation()
    new_cloud_identity = cloud_identity_schema.load(**body)

    services.provision_cloud_identity(new_cloud_identity)

    return cloud_identity_schema.dump(cloud_identity), 201
