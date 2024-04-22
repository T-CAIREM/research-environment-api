from research_environment_api.modules.monitoring_management import monitoring
from research_environment_api.web.decorators import validate_token
from research_environment_api.web.workflow import schemas, workflow_bp


@workflow_bp.get("/<workflow_id>")
@validate_token
def get_workflow(workflow_id: str):
    """Fetches the specified workflow.
    ---
    put:
      tags:
        - workflows
      description: Fetches the specified workflow.
      parameters:
      - in: path
        name: workflow_id
        schema:
          type: string
      responses:
        200:
          description: Returns the workflow.
          content:
            application/json:
              schema: Workflow
    """
    workflow = monitoring.get_workflow(workflow_id)
    serialized_workflow = schemas.Workflow().dump(workflow)
    return serialized_workflow, 200


@workflow_bp.get("/list/<user_email>")
@validate_token
def list_workflows(user_email):
    workflows_list = monitoring.list_active_workflows(user_email)
    serialized_workflows = schemas.Workflow(many=True).dump(workflows_list)
    return serialized_workflows, 200
