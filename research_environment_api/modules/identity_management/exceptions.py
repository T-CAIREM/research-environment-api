class CloudIdentityAlreadyConfiguredError(Exception):
    description = "Cloud Identity hs already been configured"
    pass


class GoogleWorkspaceUserAlreadyExistsError(Exception):
    description = "User already exists in workspace"
    pass


class BillingCreatorGroupMembershipAlreadyExistsError(Exception):
    description = "Billing Creator role has already been added to the user"
    pass
