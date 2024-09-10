import json
from os import environ

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint

from research_environment_api.web.cache import cache
from research_environment_api.web.websocket import socketio
from research_environment_api.web.config import build_config

SWAGGER_SPEC_FILE_NAME = "swagger.json"


def persist_apispec(app: Flask) -> APISpec:
    spec = APISpec(
        title="Research Environment API",
        version="1.0.0",
        openapi_version="3.0.0",
        info={"description": "Health Data Nexus Research Environment API"},
        plugins=[MarshmallowPlugin(), FlaskPlugin()],
    )

    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            spec.path(view=app.view_functions[rule.endpoint])

    with open(f"{app.static_folder}/{SWAGGER_SPEC_FILE_NAME}", "w") as f:
        f.write(json.dumps(spec.to_dict()))

    return spec


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(build_config())

    from research_environment_api.web.billing_management import billing_management_bp
    from research_environment_api.web.identity_management import identity_management_bp
    from research_environment_api.web.workbench_management import (
        workbench_management_bp,
    )
    from research_environment_api.web.workflow import workflow_bp
    from research_environment_api.web.workspace_management import (
        workspace_management_bp,
    )
    from research_environment_api.web.sharing_management import sharing_management_bp
    from research_environment_api.web.user_group_management import user_group_bp
    from research_environment_api.web.monitoring_management import (
        monitoring_management_bp,
    )
    from research_environment_api.web.healthcheck import healthcheck_management_bp

    app.register_blueprint(identity_management_bp, url_prefix="/identity")
    app.register_blueprint(billing_management_bp, url_prefix="/billing")
    app.register_blueprint(workspace_management_bp, url_prefix="/workspace")
    app.register_blueprint(workbench_management_bp, url_prefix="/workbench")
    app.register_blueprint(workflow_bp, url_prefix="/workflow")
    app.register_blueprint(sharing_management_bp, url_prefix="/sharing")
    app.register_blueprint(user_group_bp, url_prefix="/group")
    app.register_blueprint(monitoring_management_bp, url_prefix="/monitoring")
    app.register_blueprint(healthcheck_management_bp, url_prefix="/")

    cache.init_app(app)

    persist_apispec(app)
    swagger_bp = get_swaggerui_blueprint(
        "/docs",
        f"{app.static_url_path}/{SWAGGER_SPEC_FILE_NAME}",
    )
    app.register_blueprint(swagger_bp)
    socketio.init_app(
        app,
        message_queue=environ.get("CELERY_BROKER_URL"),
        ping_interval=25,
        ping_timeout=60,
    )

    return app
