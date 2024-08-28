from flask import Blueprint

healthcheck_management_bp = Blueprint("healthcheck", __name__)

from research_environment_api.web.healthcheck import views
