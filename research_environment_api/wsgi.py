import marshmallow
from celery.schedules import crontab
from dotenv import load_dotenv
from flask import jsonify

from research_environment_api.background.app import create_celery
from research_environment_api.modules.app import app as research_environment_backend_app
from research_environment_api.modules.logger import logger
from research_environment_api.web.app import create_app

load_dotenv()

research_environment_backend_app.initialize()

app = create_app()

celery = create_celery(
    research_environment_backend_app.config.celery_broker_url,
    research_environment_backend_app.config.celery_result_backend,
)


@app.errorhandler(Exception)
def handle_error(e):
    logger.exception(e)

    http_code = 500

    if isinstance(e, marshmallow.ValidationError):
        http_code = 400

    response = {"error": type(e).__name__}

    if hasattr(e, "messages"):
        response["error"] += f", {e.messages}"
    elif hasattr(e, "description"):
        response["error"] += f", {e.description}"

    return jsonify(response), http_code
