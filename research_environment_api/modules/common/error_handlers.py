"""
Centralized error handling for Google Cloud services.

This module provides consistent error handling patterns across all Google Cloud service calls,
ensuring graceful degradation when specific resources encounter issues while maintaining
operational status for other resources.
"""

import traceback
from typing import Optional, Tuple, Any
from dataclasses import dataclass
from enum import StrEnum

from research_environment_api.modules.logger import logger


class GoogleServiceErrorType(StrEnum):
    """Types of Google service errors that can be handled gracefully."""
    BILLING_DISABLED = "billing_disabled"
    API_NOT_ENABLED = "api_not_enabled"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNKNOWN = "unknown"


@dataclass
class ServiceError:
    """Represents an error encountered when calling a Google service."""
    error_type: GoogleServiceErrorType
    message: str
    resource_id: str
    service_name: str
    details: Optional[str] = None
    can_retry: bool = False


class GoogleServiceErrorHandler:
    """Centralized handler for Google Cloud service errors."""
    
    # Error message patterns and their corresponding error types
    ERROR_PATTERNS = {
        "This API method requires billing to be enabled": GoogleServiceErrorType.BILLING_DISABLED,
        "billing is disabled": GoogleServiceErrorType.BILLING_DISABLED,
        "Cloud billing is not enabled": GoogleServiceErrorType.BILLING_DISABLED,
        "billing account": GoogleServiceErrorType.BILLING_DISABLED,
        "has not been used in project": GoogleServiceErrorType.API_NOT_ENABLED,
        "API has not been used": GoogleServiceErrorType.API_NOT_ENABLED,
        "Permission denied": GoogleServiceErrorType.PERMISSION_DENIED,
        "Access denied": GoogleServiceErrorType.PERMISSION_DENIED,
        "not found": GoogleServiceErrorType.NOT_FOUND,
        "Quota exceeded": GoogleServiceErrorType.QUOTA_EXCEEDED,
    }
    
    @classmethod
    def handle_google_service_error(
        cls,
        error: Exception,
        resource_id: str,
        service_name: str,
        operation: str
    ) -> ServiceError:
        """
        Handle a Google Cloud service error and return a structured error object.
        
        Args:
            error: The exception that was raised
            resource_id: ID of the resource that caused the error (e.g., project_id)
            service_name: Name of the Google service (e.g., "Compute Engine")
            operation: The operation being performed (e.g., "list_instances")
            
        Returns:
            ServiceError object with structured error information
        """
        error_str = str(error)
        error_type = cls._classify_error(error_str)
        
        # Log the error with full context
        logger.error(
            f"Google {service_name} error for {resource_id} during {operation}: {error_str}",
            extra={
                "resource_id": resource_id,
                "service_name": service_name,
                "operation": operation,
                "error_type": error_type.value,
                "traceback": traceback.format_exc()
            }
        )
        
        # Generate user-friendly message
        user_message = cls._generate_user_message(error_type, resource_id, error_str)
        
        return ServiceError(
            error_type=error_type,
            message=user_message,
            resource_id=resource_id,
            service_name=service_name,
            details=error_str,
            can_retry=error_type in [GoogleServiceErrorType.QUOTA_EXCEEDED]
        )
    
    @classmethod
    def _classify_error(cls, error_message: str) -> GoogleServiceErrorType:
        """Classify the error based on the error message."""
        for pattern, error_type in cls.ERROR_PATTERNS.items():
            if pattern in error_message:
                return error_type
        return GoogleServiceErrorType.UNKNOWN
    
    @classmethod
    def _generate_user_message(
        cls,
        error_type: GoogleServiceErrorType,
        resource_id: str,
        error_details: str
    ) -> str:
        """Generate a user-friendly error message."""
        if error_type == GoogleServiceErrorType.BILLING_DISABLED:
            return (
                f"Billing is disabled for {resource_id}. "
                f"Please enable billing at "
                f"https://console.developers.google.com/billing/enable?project={resource_id}"
            )
        elif error_type == GoogleServiceErrorType.API_NOT_ENABLED:
            return f"Required APIs are not enabled for {resource_id}. The resource may still be provisioning."
        elif error_type == GoogleServiceErrorType.PERMISSION_DENIED:
            return f"Access denied to {resource_id}. Check your permissions."
        elif error_type == GoogleServiceErrorType.NOT_FOUND:
            return f"Resource {resource_id} not found or has been deleted."
        elif error_type == GoogleServiceErrorType.QUOTA_EXCEEDED:
            return f"Quota exceeded for {resource_id}. Please try again later."
        else:
            return f"Service error for {resource_id}: {error_details}"


def safe_google_service_call(
    func: callable,
    resource_id: str,
    service_name: str,
    operation: str,
    default_return: Any = None
) -> Tuple[Any, Optional[ServiceError]]:
    """
    Safely call a Google service function with error handling.
    
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
        error = GoogleServiceErrorHandler.handle_google_service_error(
            e, resource_id, service_name, operation
        )
        return default_return, error