from flask import Blueprint

identity_management_bp = Blueprint("identity_management", __name__)

import research_environment_api.web.identity_management.views
