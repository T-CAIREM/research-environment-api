from research_environment_api.web.healthcheck import (
    healthcheck_management_bp
)


@healthcheck_management_bp.get("/")
def healthcheck():
    return "App available", 200
