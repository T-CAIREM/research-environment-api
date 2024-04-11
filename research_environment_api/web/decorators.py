from flask import jsonify, request
from functools import wraps
from google.auth.transport import requests
from google.oauth2 import id_token

# this will be moved to env
AUDIENCE = "https://research-environment-api-dev-core-onbon2ktya-uc.a.run.app"
# AUDIENCE = "http://host.docker.internal:5000"


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
