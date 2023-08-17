from research_environment_api.modules.monitoring import services
from research_environment_api.web.monitoring import (
    monitoring_bp,
)


@monitoring_bp.get("/<workflow_id>")
def get_workflow(workflow_id: str):
    workflow = services.get_workflow(workflow_id)
    return {
        "id": workflow.id,
        "build_type": workflow.build_type.value,
        "status": workflow.build_status.value,
        "error": workflow.build_error_information,
    }, 200
