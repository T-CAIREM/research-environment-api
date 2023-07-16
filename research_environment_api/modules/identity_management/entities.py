from dataclasses import dataclass, field

from research_environment_api.modules.app import config


@dataclass
class CloudIdentityCreation:
    user_name: str
    password: str
    primary_email: str = field(init=False)
    recovery_email: str
    family_name: str
    given_name: str

    def __post_init__(self):
        organization_domain = config.organization_domain
        self.primary_email = f"{self.user_name}@{organization_domain}"
