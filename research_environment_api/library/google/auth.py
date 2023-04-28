from typing import Callable, List, Type
from functools import wraps

from google.oauth2 import service_account


def with_delegated_client(client_class: Type, scopes: List[str]):
    def wrapper(function: Callable):
        @wraps(function)
        def inner(
            user_email: str, credentials: service_account.Credentials, *args, **kwargs
        ):
            scoped_credentials = credentials.with_scopes(scopes)
            delegated_credentials = scoped_credentials.with_subject(user_email)
            client = client_class(credentials=delegated_credentials)
            return function(client, *args, **kwargs)

        return inner

    return wrapper
