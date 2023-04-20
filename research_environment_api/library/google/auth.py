import google.auth


def create_delegated_credentials_for(
    user_email: str, credentials: google.auth.Credentials = google.auth.default()
) -> google.auth.Credentials:
    return credentials.with_subject(user_email)
