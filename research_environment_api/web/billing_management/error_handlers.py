import marshmallow

from research_environment_api.modules.billing_management import exceptions
from research_environment_api.web.billing_management import billing_management_bp

# How long a caller should wait before retrying a share or revoke that ran out
# of retries: long enough for a burst of concurrent changes to settle.
RETRY_AFTER_SECONDS = 30


@billing_management_bp.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(error):
    return error.messages_dict, 422


@billing_management_bp.errorhandler(exceptions.BillingAccessUpdateUnavailableError)
def handle_billing_access_update_unavailable_error(error):
    # 503 + Retry-After rather than 409: the request is valid and will succeed
    # unchanged once the contention or the upstream error clears. This API uses
    # 409 for conflicts that retrying cannot fix (identity already configured).
    return (
        {"error": error.description},
        503,
        {"Retry-After": str(RETRY_AFTER_SECONDS)},
    )
