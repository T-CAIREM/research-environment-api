from flask import render_template

from research_environment_api.web.decorators import validate_token, validate_admin_page_auth
from research_environment_api.web.admin_panel_management import (
    admin_panel_management_bp,
    schemas,
)


@admin_panel_management_bp.route('/')
@validate_admin_page_auth
@validate_token
def admin_home():
    """Admin panel home page"""
    return render_template('admin_panel/home.html')


@admin_panel_management_bp.route('/celery')
@validate_admin_page_auth
@validate_token
def celery_management():
    """Celery management page"""
    return render_template('admin_panel/celery_management_home.html')
