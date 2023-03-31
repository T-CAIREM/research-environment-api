import marshmallow
from flask import request

from billing_management.web import app, schemas


@app.route("/link", methods=["POST"])
def link_billing_account():
    body = request.get_json()
    billing_account_creation_schema = schemas.BillingAccountCreation()
    new_billing_account = billing_account_creation_schema.load(body)

    billing_account_schema = schemas.BillingAccount()
    created_billing_account = billing_account_schema.dump({})

    return created_billing_account, 200


@app.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422
