class CloudIdentityAlreadyConfiguredError(Exception):
    description = "Cloud Identity hs already been configured"
    pass


class GoogleWorkspaceUserAlreadyExistsError(Exception):
    description = "User already exists in workspace"
    pass


class BillingCreatorGroupMembershipAlreadyExistsError(Exception):
    description = "Billing Creator role has already been added to the user"
    pass


class GoogleWorkspaceAuthorizationError(Exception):
    description = (
        "The platform is not authorized to manage Google Workspace identities. "
        "An administrator must verify the service account's domain-wide "
        "delegation registration and its scopes"
    )
    pass
