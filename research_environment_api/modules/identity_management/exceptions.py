from typing import Self


class CloudIdentityAlreadyConfiguredError(Exception):
    def __init__(
        self, message="Cloud Identity already configured", *args, **kwargs
    ) -> Self:
        super().__init__(message, *args, **kwargs)


class GoogleWorkspaceUserAlreadyExistsError(Exception):
    pass


class BillingCreatorGroupMembershipAlreadyExistsError(Exception):
    pass
