from research_environment_api.web.workflow import (
    workflow_bp,
)
from research_environment_api.modules.workbench_management import monitoring


@workflow_bp.get("/<workflow_id>")
def get_workflow(workflow_id: str):
    workflow = monitoring.get_workflow(workflow_id)
    return {
        "id": workflow.id,
        "build_type": workflow.build_type.value,
        "status": workflow.build_status.value,
        "error": workflow.build_error_information,
    }, 200
