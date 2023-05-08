from typing import Optional

from google.cloud import asset
from google.oauth2 import service_account


def list_iam_policies(
    credentials: service_account.Credentials,
    email: str,
    organization_id: str,
    resource: str,
):
    client = asset.AssetServiceClient(credentials=credentials)
    scope = f"organizations/{organization_id}"
    query = f"{resource} policy: {email}"

    return client.search_all_iam_policies(request={"scope": scope, "query": query})


def assign_policy(email: str, policy: str, resource: Optional[str] = None):
    pass
