import random
from typing import List, Optional

from research_environment_api.background import builds, constants, workflows
from research_environment_api.modules.workbench_management import entities


def create_jupyter_notebook(
    workbench_creation_request: entities.WorkbenchCreation,
    available_zones: Optional[List[str]] = None,
):
    if not available_zones:
        zones = constants.AVAILABLE_ZONES[workbench_creation_request.region]
        available_zones = random.sample(zones, len(zones))

    zone, *fallback_zones = available_zones

    build = builds.create_jupyter_workbench_build(
        zone=zone, **workbench_creation_request
    )
    return workflows.create_jupyter_notebook(
        build=build,
        user_email=workbench_creation_request.user_email,
        fallback_zones=fallback_zones,
    )()


def stop_jupyter_workbench(workbench_stop_request: entities.WorkbenchStop):
    return workflows.stop_jupyter_workbench(**workbench_stop_request)()
