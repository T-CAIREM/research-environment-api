from flask import Flask


def create_app(config_object: str):
    app = Flask(__name__)
    app.config.from_object(config_object)

    from research_environment_api.modules.model import db, migrate

    db.init_app(app)
    migrate.init_app(app)

    from research_environment_api.web.identity_management import identity_management_bp
    from research_environment_api.web.billing_management import billing_management_bp

    app.register_blueprint(identity_management_bp, url_prefix="/identity")
    app.register_blueprint(billing_management_bp, url_prefix="/billing")

    return app
