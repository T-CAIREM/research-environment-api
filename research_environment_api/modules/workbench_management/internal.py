from research_environment_api.modules.config import config


def create_cloud_build_source():
    return {
        "repoSource": {
            "project_id": config.terraform_project_id,
            "repo_name": config.terraform_repo_name,
            "branch_name": config.terraform_branch_name,
        }
    }
