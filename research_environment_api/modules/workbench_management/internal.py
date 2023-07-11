import random
from copy import deepcopy

from research_environment_api.modules.config import config
from research_environment_api.modules.workbench_management.constants import (
    AVAILABLE_ZONES,
)


def create_cloud_build_source():
    return {
        "repo_source": {
            "project_id": config.project_id,
            "repo_name": config.terraform_repo_name,
            "branch_name": config.terraform_branch_name,
        }
    }


def get_available_zones(region: str):
    available_zones = deepcopy(AVAILABLE_ZONES[region])
    random.shuffle(available_zones)
    return "-".join([region, available_zones.pop(0)]), available_zones
