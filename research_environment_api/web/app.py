from flask import Flask

from research_environment_api.web.identity_management import identity_management_bp


def create_app(config_object: str):
    app = Flask(__name__)
    app.config.from_object(config_object)

    from research_environment_api.modules.model import db, migrate

    db.init_app(app)
    migrate.init_app(app)

    app.register_blueprint(identity_management_bp)

    return app
