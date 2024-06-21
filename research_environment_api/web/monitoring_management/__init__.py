from flask import Blueprint

monitoring_management_bp = Blueprint("monitoring_management", __name__)

from research_environment_api.web.monitoring_management import views
