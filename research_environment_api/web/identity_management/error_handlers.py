import marshmallow

from research_environment_api.web.identity_management import identity_management_bp
from research_environment_api.modules.identity_management import exceptions


@identity_management_bp.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422


@identity_management_bp.errorhandler(exceptions.CloudIdentityAlreadyConfiguredError)
def handle_validation_error(error):
    return str(error), 409
