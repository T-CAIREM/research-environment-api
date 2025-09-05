AVAILABLE_ZONES = {
    "us-central1": ["us-central1-a", "us-central1-b", "us-central1-c"],
    "northamerica-northeast1": [
        "northamerica-northeast1-a",
        "northamerica-northeast1-b",
        "northamerica-northeast1-c",
    ],
    "europe-west3": ["europe-west3-a", "europe-west3-b", "europe-west3-c"],
    "australia-southeast1": [
        "australia-southeast1-a",
        "australia-southeast1-b",
        "australia-southeast1-c",
    ],
}

CLOUD_BUILD_ERROR_MESSAGE = {
    14: "Insufficient resources in the selected region. Please try again later.",
    7: "Exceeded quota limits. Please check your quota and try again.",
    43: "Permission denied. Please check IAM permissions.",
    44: "Resource not found. Please verify resource names or configurations.",
    40: "Client-side HTTP error. Review permissions or request format.",
    50: "Server-side HTTP error. This may be temporary—please retry later.",
}
