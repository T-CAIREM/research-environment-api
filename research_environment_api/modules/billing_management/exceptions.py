class BillingAccessUpdateUnavailableError(Exception):
    description = (
        "The billing account's access policy could not be updated right now: "
        "it kept changing concurrently, or Google Cloud Billing returned a "
        "transient error. The request is safe to retry later"
    )
