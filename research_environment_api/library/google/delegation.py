from typing import Callable, List
from functools import wraps

from google.oauth2 import service_account


def delegated(scopes: List[str]):
    def wrapper(function: Callable):
        @wraps(function)
        def inner(
            user_email: str, credentials: service_account.Credentials, *args, **kwargs
        ):
            scoped_credentials = credentials.with_scopes(scopes)
            delegated_credentials = scoped_credentials.with_subject(user_email)
            return function(delegated_credentials, *args, **kwargs)

        return inner

    return wrapper
