from research_environment_api.web.workflow import (
    workflow_bp,
)
from research_environment_api.modules.workbench_management import monitoring
from research_environment_api.web.workflow import schemas


@workflow_bp.get("/<workflow_id>")
def get_workflow(workflow_id: str):
    workflow = monitoring.get_workflow(workflow_id)
    serialized_workflow = schemas.Workflow().dump(workflow)
    return serialized_workflow, 200
