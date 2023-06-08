from typing import List

from google.oauth2 import service_account


def domain_delegate_credentials(
    credentials: service_account, user_email: str, scopes: List[str]
) -> service_account.Credentials:
    scoped_credentials = credentials.with_scopes(scopes)
    delegated_credentials = scoped_credentials.with_subject(user_email)

    return delegated_credentials
