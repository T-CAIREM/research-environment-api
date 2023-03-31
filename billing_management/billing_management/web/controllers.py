import marshmallow
from flask import request

from billing_management.web import app, schemas


@app.route("/link", methods=["POST"])
def link_billing_account():
    body = request.get_json()
    billing_account_creation_schema = schemas.BillingAccountCreation()
    billing_account = billing_account_creation_schema.load(body)

    linked_billing_account = services.link_billing_account(billing_account)
    billing_account_schema = schemas.BillingAccount()
    serialized_billing_account = billing_account_schema.dump(linked_billing_account)

    return serialized_billing_account, 200


@app.route("/unlink", methods=["DELETE"])
def unlink_billing_account():
    return "Unimplemented", 501


@app.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422
