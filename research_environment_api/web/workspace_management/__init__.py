from flask import Blueprint

workspace_management_bp = Blueprint("workspace_management", __name__)

from research_environment_api.web.workspace_management import views, error_handlers
