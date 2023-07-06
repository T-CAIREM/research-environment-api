from dataclasses import dataclass, field
from research_environment_api.modules.config import config


@dataclass
class JupyterWorkbench:
    machine_type: str
    user_project_id: str
    dataset: str
    email_id: str
    bucket_name: str
    region: str
    persistent_disk: str
    gpu_accelerator: str
    zone: str = field(init=False)
    jupyter_startup_script_bucket: str = field(init=False)

    def __post_init__(self):
        self.jupyter_startup_script_bucket = config.jupyter_startup_script
