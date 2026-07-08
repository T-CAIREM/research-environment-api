import marshmallow
from dotenv import load_dotenv
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

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
    response = {"error": type(e).__name__}

    if hasattr(e, "messages"):
        response["error"] += f", {e.messages}"
    elif hasattr(e, "description"):
        response["error"] += f", {e.description}"

    # Expected HTTP errors (404, 405, 403, ...) carry their own status code.
    # Return it verbatim and log a single line instead of a full traceback: the
    # public endpoint is constantly probed by internet scanners requesting paths
    # like /.env or /.git/config, which would otherwise flood the logs with
    # tracebacks and — worse — be reported back to clients as 500s.
    if isinstance(e, HTTPException):
        logger.info(
            "%s %s -> %s %s", request.method, request.path, e.code, type(e).__name__
        )
        return jsonify(response), e.code

    # Client-side validation failures are 400s, not server errors.
    if isinstance(e, marshmallow.ValidationError):
        logger.info(
            "Validation error on %s %s: %s", request.method, request.path, e.messages
        )
        return jsonify(response), 400

    # Anything else is a genuine, unexpected server error — keep the traceback.
    logger.exception(e)
    return jsonify(response), 500
