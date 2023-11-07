from flask import Blueprint

sharing_management_bp = Blueprint("sharing_management", __name__)

from research_environment_api.web.sharing_management import views
