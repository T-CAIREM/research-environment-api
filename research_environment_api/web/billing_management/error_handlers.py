import marshmallow

from research_environment_api.web.billing_management import billing_management_bp
from research_environment_api.modules.billing_management import exceptions


@billing_management_bp.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422


@billing_management_bp.errorhandler(exceptions.InsufficientPermissionError)
def handle_insufficient_permission_error(error):
    return error.message, 403
