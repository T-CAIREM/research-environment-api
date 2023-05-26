import requests


class WorkspaceControllerApiClient:
    def __init__(self, api_url, credentials):
        self.api_url = api_url
        self.credentials = credentials

    def create_workspace(self, gcp_user_id: str, region: str, billing_account_id: str):
        json = {
            "userid": gcp_user_id,
            "billingid": billing_account_id,
            "region": region,
        }
        create_workspace_request = requests.Request(
            "POST", url="/workspace/create", json=json
        )
        return self._make_api_request(create_workspace_request)

    def _make_api_request(self, request: requests.Request) -> requests.Response:
        session = requests.Session()
        request.url = f"{self.api_url}{request.url}"
        prepped = request.prepare()
        self.credentials.before_request(
            None, request.method, request.url, request.headers
        )

        response = session.send(prepped)
        response.raise_for_status()

        return response
