from research_environment_api.modules.config import config
from research_environment_api.modules.workbench_management.entities import Workbench


def list_workbenches(gcp_project_id: str):
    compute_engine_client = config.google_compute_engine_client
    gce_instances = compute_engine_client.list_instances(project=gcp_project_id)

    return [
        Workbench.from_gce_instance(instance)
        for _, instance_list in gce_instances
        for instance in instance_list.instances
    ]
