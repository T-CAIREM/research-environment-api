from flask import Blueprint

workflow_bp = Blueprint("workflow", __name__)

from research_environment_api.web.workflow import views
