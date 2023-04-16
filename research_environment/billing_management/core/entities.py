from typing import Self
from dataclasses import dataclass


@dataclass
class BillingAccount:
    cloud_identity_id: str
    account_number: str
