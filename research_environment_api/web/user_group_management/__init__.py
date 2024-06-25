from flask import Blueprint

user_group_bp = Blueprint("user_group_management", __name__)

from research_environment_api.web.user_group_management import views
