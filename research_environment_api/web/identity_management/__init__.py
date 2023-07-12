from flask import Blueprint

identity_management_bp = Blueprint("identity_management", __name__)

from research_environment_api.web.identity_management import error_handlers, views
