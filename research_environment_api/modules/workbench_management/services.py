from research_environment_api.modules import config


def fetch_workbench_info(gcp_project_id: str):
    compute_engine_client = config.app_config().google_compute_engine_client
    return compute_engine_client.list_instances(project=gcp_project_id)
