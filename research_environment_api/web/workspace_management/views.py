from research_environment_api.web.workspace_management import workspace_management_bp


@workspace_management_bp.post("/create")
def create_workspace():
    return "", 201
