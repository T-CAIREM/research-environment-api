from requests import Request
import os
from research_environment_api.library.legacy_api.decorators import api_request


@api_request
def create_workspace(gcp_user_id: str, region: str, billing_account_id: str):
    json = {"userid": gcp_user_id, "billingid": billing_account_id, "region": region}
    request = Request("POST", url="/workspace/create", json=json)
    return request
