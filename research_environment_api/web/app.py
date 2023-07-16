from flask import Flask

from research_environment_api.web.cache import cache


def create_app():
    app = Flask(__name__)

    from research_environment_api.web.billing_management import billing_management_bp
    from research_environment_api.web.identity_management import identity_management_bp
    from research_environment_api.web.workbench_management import (
        workbench_management_bp,
    )
    from research_environment_api.web.workspace_management import (
        workspace_management_bp,
    )

    app.register_blueprint(identity_management_bp, url_prefix="/identity")
    app.register_blueprint(billing_management_bp, url_prefix="/billing")
    app.register_blueprint(workspace_management_bp, url_prefix="/workspace")
    app.register_blueprint(workbench_management_bp, url_prefix="/workbench")

    cache.init_app(app)

    return app
