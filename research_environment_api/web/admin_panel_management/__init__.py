from flask import Blueprint

admin_panel_management_bp = Blueprint("admin_panel_management", __name__)

from research_environment_api.web.admin_panel_management import views
