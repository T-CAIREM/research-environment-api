"""
Simplified error handling for Google Cloud services.

This module provides minimal error handling patterns across all Google Cloud service calls,
ensuring graceful degradation when specific resources encounter issues while maintaining
operational status for other resources.
"""

from typing import Optional, Tuple, Any
from dataclasses import dataclass

from research_environment_api.modules.logger import logger


@dataclass
class ServiceError:
    """Represents an error encountered when calling a Google service."""

    error_type: str
    message: str
    resource_id: str
    service_name: str
    details: Optional[str] = None
    can_retry: bool = False


def safe_google_service_call(
    func: callable,
    resource_id: str,
    service_name: str,
    operation: str,
    default_return: Any = None,
) -> Tuple[Any, Optional[ServiceError]]:
    """
    Safely call a Google service function with simplified error handling.

    Args:
        func: The function to call
        resource_id: ID of the resource being accessed
        service_name: Name of the Google service
        operation: Description of the operation
        default_return: Default value to return on error

    Returns:
        Tuple of (result, error) where error is None on success
    """
    try:
        result = func()
        return result, None
    except Exception as e:
        error_str = str(e)

        # Simple logging
        logger.error(
            f"Google {service_name} error for {resource_id} during {operation}: {error_str}"
        )

        # Generate user-friendly message and classify error
        error_type, user_message = _classify_and_generate_message(
            error_str, resource_id
        )

        error = ServiceError(
            error_type=error_type,
            message=user_message,
            resource_id=resource_id,
            service_name=service_name,
            details=error_str,
            can_retry=error_type == "quota_exceeded",
        )
        return default_return, error


def _classify_and_generate_message(error_str: str, resource_id: str) -> tuple[str, str]:
    """Classify error and generate user-friendly message in one step."""

    error_patterns = {
        "billing_disabled": {
            "patterns": [
                "billing",
                "Cloud billing is not enabled",
                "This API method requires billing",
            ],
            "message": (
                f"Billing is disabled for {resource_id}. "
                f"Please enable billing at "
                f"https://console.developers.google.com/billing/enable?project={resource_id}"
            ),
        },
        "api_not_enabled": {
            "patterns": ["API has not been used", "has not been used in project"],
            "message": f"Required APIs are not enabled for {resource_id}. The resource may still be provisioning.",
        },
        "permission_denied": {
            "patterns": ["Permission denied", "Access denied"],
            "message": f"Access denied to {resource_id}. Check your permissions.",
        },
        "not_found": {
            "patterns": ["not found"],
            "message": f"Resource {resource_id} not found or has been deleted.",
        },
        "quota_exceeded": {
            "patterns": ["Quota exceeded"],
            "message": f"Quota exceeded for {resource_id}. Please try again later.",
        },
    }

    for error_type, config in error_patterns.items():
        if any(pattern in error_str for pattern in config["patterns"]):
            return error_type, config["message"]

    return "unknown", f"Service error for {resource_id}: {error_str}"
