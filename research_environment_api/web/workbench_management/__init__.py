from flask import Blueprint

workbench_management_bp = Blueprint("workbench_management", __name__)

from research_environment_api.web.workbench_management import views
