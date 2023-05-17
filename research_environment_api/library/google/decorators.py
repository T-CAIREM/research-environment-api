from functools import wraps
from typing import Callable
import google.auth.jwt as jwt
import os

from requests import Request, Response, Session


def load_jwt_credentials() -> jwt.Credentials:
    credentials = jwt.Credentials.from_service_account_file(
        os.environ["GATEWAY_SERVICE_ACCOUNT_CREDENTIALS_PATH"],
        audience=os.environ["GATEWAY_AUDIENCE"],
    )
    return credentials


def apply_api_credentials(request: Request) -> None:
    credentials = load_jwt_credentials()
    credentials.before_request(None, request.method, request.url, request.headers)


def api_request(request_creator_callable: Callable[..., Request]) -> Callable:
    @wraps(request_creator_callable)
    def wrapper(*args, **kwargs) -> Response:
        session = Session()
        request = request_creator_callable(*args, **kwargs)
        request.url = request.url
        prepped = request.prepare()
        apply_api_credentials(prepped)
        return session.send(prepped)

    return wrapper
