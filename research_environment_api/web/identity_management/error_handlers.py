import marshmallow

from research_environment_api.modules.identity_management import exceptions
from research_environment_api.web.identity_management import identity_management_bp


@identity_management_bp.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422


@identity_management_bp.errorhandler(exceptions.CloudIdentityAlreadyConfiguredError)
def handle_cloud_identity_already_configured_error(error):
    return str(error), 409


@identity_management_bp.errorhandler(exceptions.GoogleWorkspaceAuthorizationError)
def handle_google_workspace_authorization_error(error):
    # 502 rather than 403: the caller is authorised, the upstream Google
    # Workspace dependency rejected this service's credentials.
    return error.description, 502
