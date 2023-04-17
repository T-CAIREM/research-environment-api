from flask import Flask

from research_environment.identity_management.web import identity_management_bp


def create_app(config_object: str):
    app = Flask(__name__)
    app.config.from_object(config_object)

    from research_environment.db import db

    db.init_app(app)

    app.register_blueprint(identity_management_bp)
