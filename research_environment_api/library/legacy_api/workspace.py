from requests import Request

from research_environment_api.library.legacy_api.decorators import api_request


class ProjectAlreadyExistsError(Exception):
    pass


class ProjectsPerBillingAccountExceededError(Exception):
    pass


@api_request
def create_workspace(gcp_user_id: str, region: str, billing_account_id: str):
    json = {"userid": gcp_user_id, "billingid": billing_account_id, "region": region}
    return Request("POST", url="/workspace/create", json=json)
