from os import environ
from functools import wraps

from flask import jsonify, request, make_response
from google.auth.transport import requests
from google.oauth2 import id_token

from research_environment_api.modules.admin_panel_management import services

AUDIENCE = environ.get("CLOUD_RESEARCH_ENVIRONMENTS_API_URL")


def validate_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Missing token"}), 401

        token = token.split("Bearer ")[-1]
        result = id_token.verify_oauth2_token(token, requests.Request(), AUDIENCE)

        if result["aud"] != AUDIENCE:
            return jsonify({"error": "Invalid audience"}), 401

        return func(*args, **kwargs)

    return wrapper


def validate_admin_page_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not services.authenticate_admin(auth.username, auth.password):
            response = make_response("Could not verify your credentials for the admin area", 401)
            response.headers["WWW-Authenticate"] = 'Basic realm="Admin Panel"'
            return response
        return func(*args, **kwargs)

    return wrapper
