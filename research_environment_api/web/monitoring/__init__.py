from flask import Blueprint

monitoring_bp = Blueprint("monitoring", __name__)

from research_environment_api.web.monitoring import views
