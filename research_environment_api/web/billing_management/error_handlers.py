import marshmallow

from research_environment_api.web.billing_management import billing_management_bp


@billing_management_bp.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422
