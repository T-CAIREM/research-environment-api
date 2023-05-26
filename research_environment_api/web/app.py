from flask import Flask


def create_app(config_object: str):
    app = Flask(__name__)
    app.config.from_object(config_object)

    from research_environment_api.web.identity_management import identity_management_bp
    from research_environment_api.web.billing_management import billing_management_bp
    from research_environment_api.web.workspace_management import (
        workspace_management_bp,
    )

    app.register_blueprint(identity_management_bp, url_prefix="/identity")
    app.register_blueprint(billing_management_bp, url_prefix="/billing")
    app.register_blueprint(workspace_management_bp, url_prefix="/workspace")

    return app
