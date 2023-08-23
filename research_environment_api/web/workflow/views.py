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


@workflow_bp.get("/list/<user_email>")
def list_workflows(user_email):
    workflows_list = monitoring.list_active_workflows(user_email)
    serialized_workflows = schemas.Workflow(many=True).dump(workflows_list)
    return serialized_workflows, 200
