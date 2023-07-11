from dataclasses import dataclass


@dataclass
class BillingAccount:
    id: str
    name: str
    cloud_link: str
    is_owner: bool
