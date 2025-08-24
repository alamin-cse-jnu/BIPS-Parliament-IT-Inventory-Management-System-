"""
PRP API Custom Exceptions Module
================================

Custom exceptions for PRP (Parliament Resource Portal) API operations in PIMS
(Parliament IT Inventory Management System).

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Proper error handling for API failures, authentication issues, and sync operations

Dependencies:
- Depends on users/api/__init__.py (package init)

Exception Hierarchy:
- PRPException (Base)
  ├── PRPConnectionError (Network/HTTP issues)
  ├── PRPAuthenticationError (Token/auth failures)  
  ├── PRPSyncError (Data synchronization failures)
  ├── PRPRateLimitError (API rate limiting)
  ├── PRPDataValidationError (Invalid response data)
  └── PRPConfigurationError (Setup/config issues)

Usage Example:
    from users.api.exceptions import PRPConnectionError, PRPAuthenticationError
    
    try:
        result = prp_client.get_employee_details(department_id=1)
    except PRPAuthenticationError as e:
        logger.error(f"PRP authentication failed: {e}")
    except PRPConnectionError as e:  
        logger.error(f"PRP connection error: {e}")
"""

import logging
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


class PRPException(Exception):
    """
    Base exception class for all PRP API related errors.
    
    All PRP-specific exceptions inherit from this class to provide
    consistent error handling across the integration.
    
    Attributes:
        message (str): Human-readable error message
        error_code (str): Internal error code for logging/tracking
        details (dict): Additional error context/details
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "PRP_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.message}', error_code='{self.error_code}')"


class PRPConnectionError(PRPException):
    """
    Raised when connection to PRP API fails.
    
    This includes network timeouts, DNS resolution failures, 
    connection refused, and other HTTP-level connection issues.
    
    Business Impact: Prevents user sync operations
    Recovery: Retry with exponential backoff, check network connectivity
    
    Examples:
        - Network timeout connecting to https://prp.parliament.gov.bd
        - DNS resolution failure for PRP domain
        - Connection refused (PRP server down)
        - SSL/TLS handshake failures
    """
    
    def __init__(
        self, 
        message: str = "Failed to connect to PRP API", 
        url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if url:
            error_details['url'] = url
        if timeout_seconds:
            error_details['timeout_seconds'] = timeout_seconds
            
        super().__init__(
            message=message,
            error_code="PRP_CONNECTION_ERROR", 
            details=error_details
        )
        
        # Log connection failures for monitoring
        logger.warning(
            f"PRP Connection Error: {message}",
            extra={
                'url': url,
                'timeout': timeout_seconds,
                'details': error_details
            }
        )


class PRPAuthenticationError(PRPException):
    """
    Raised when PRP API authentication fails.
    
    This covers token acquisition failures, token refresh failures,
    invalid credentials, and expired tokens.
    
    Business Impact: Blocks all PRP operations until credentials fixed
    Recovery: Check credentials, refresh tokens, contact PRP admin
    
    Examples:
        - Invalid username/password for token acquisition
        - Expired bearer token  
        - Token refresh failure
        - Account locked/disabled in PRP
    """
    
    def __init__(
        self, 
        message: str = "PRP authentication failed",
        auth_step: Optional[str] = None,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if auth_step:
            error_details['auth_step'] = auth_step
        if username:
            # Log username but not password for security
            error_details['username'] = username
            
        super().__init__(
            message=message,
            error_code="PRP_AUTH_ERROR",
            details=error_details
        )
        
        # Log auth failures for security monitoring
        logger.error(
            f"PRP Authentication Error: {message}",
            extra={
                'auth_step': auth_step,
                'username': username,
                'details': error_details
            }
        )


class PRPSyncError(PRPException):
    """
    Raised when user data synchronization from PRP fails.
    
    This covers data mapping failures, database update errors,
    business rule violations, and sync state inconsistencies.
    
    Business Impact: User data may be stale or inconsistent
    Recovery: Retry sync, check data mappings, validate business rules
    
    Examples:
        - Failed to map PRP userId to PIMS employee_id
        - Department not found for PRP employee
        - Database constraint violation during sync
        - Status mapping conflicts (PRP active vs PIMS inactive)
    """
    
    def __init__(
        self, 
        message: str = "PRP user sync failed",
        sync_operation: Optional[str] = None,
        user_id: Optional[str] = None,
        department_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if sync_operation:
            error_details['sync_operation'] = sync_operation
        if user_id:
            error_details['user_id'] = user_id
        if department_id:
            error_details['department_id'] = department_id
            
        super().__init__(
            message=message,
            error_code="PRP_SYNC_ERROR",
            details=error_details
        )
        
        # Log sync failures for operational monitoring
        logger.error(
            f"PRP Sync Error: {message}",
            extra={
                'operation': sync_operation,
                'user_id': user_id,
                'department_id': department_id,
                'details': error_details
            }
        )


class PRPRateLimitError(PRPException):
    """
    Raised when PRP API rate limits are exceeded.
    
    PRP API may have request limits per minute/hour to prevent abuse.
    This exception handles rate limiting scenarios.
    
    Business Impact: Temporary delay in sync operations
    Recovery: Wait for rate limit reset, implement exponential backoff
    
    Examples:
        - Exceeded 100 requests per minute limit
        - Concurrent sync operations hitting limits
        - Bulk department sync triggering rate limits
    """
    
    def __init__(
        self, 
        message: str = "PRP API rate limit exceeded",
        retry_after_seconds: Optional[int] = None,
        request_count: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if retry_after_seconds:
            error_details['retry_after_seconds'] = retry_after_seconds
        if request_count:
            error_details['request_count'] = request_count
            
        super().__init__(
            message=message,
            error_code="PRP_RATE_LIMIT_ERROR",
            details=error_details
        )
        
        # Log rate limit hits for API usage monitoring
        logger.warning(
            f"PRP Rate Limit Hit: {message}",
            extra={
                'retry_after': retry_after_seconds,
                'request_count': request_count,
                'details': error_details
            }
        )


class PRPDataValidationError(PRPException):
    """
    Raised when PRP API returns invalid or unexpected data.
    
    This covers malformed JSON responses, missing required fields,
    invalid data types, and schema validation failures.
    
    Business Impact: Cannot process PRP data for sync
    Recovery: Check API response format, validate data schema
    
    Examples:
        - Missing 'userId' field in employee details
        - Invalid email format in PRP response
        - Null values for required fields
        - Response schema changes in PRP API
    """
    
    def __init__(
        self, 
        message: str = "Invalid data received from PRP API",
        field_name: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field_name:
            error_details['field_name'] = field_name
        if expected_type:
            error_details['expected_type'] = expected_type
        if actual_value is not None:
            error_details['actual_value'] = str(actual_value)
            
        super().__init__(
            message=message,
            error_code="PRP_DATA_VALIDATION_ERROR",
            details=error_details
        )
        
        # Log validation failures for API monitoring
        logger.error(
            f"PRP Data Validation Error: {message}",
            extra={
                'field': field_name,
                'expected': expected_type,
                'actual': actual_value,
                'details': error_details
            }
        )


class PRPConfigurationError(PRPException):
    """
    Raised when PRP integration configuration is invalid.
    
    This covers missing settings, invalid URLs, credential issues,
    and other configuration-related problems.
    
    Business Impact: PRP integration cannot initialize
    Recovery: Check Django settings, verify configuration
    
    Examples:
        - Missing PRP_API_BASE_URL in settings
        - Invalid PRP credentials in environment variables
        - Missing required Django app configuration
        - Database migration not applied for PRP fields
    """
    
    def __init__(
        self, 
        message: str = "PRP integration configuration error",
        config_key: Optional[str] = None,
        expected_value: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if config_key:
            error_details['config_key'] = config_key
        if expected_value:
            error_details['expected_value'] = expected_value
            
        super().__init__(
            message=message,
            error_code="PRP_CONFIG_ERROR",
            details=error_details
        )
        
        # Log configuration errors for deployment monitoring
        logger.critical(
            f"PRP Configuration Error: {message}",
            extra={
                'config_key': config_key,
                'expected': expected_value,
                'details': error_details
            }
        )


# Convenience function for wrapping external exceptions
def wrap_external_exception(
    original_exception: Exception,
    operation: str = "PRP API operation",
    context: Optional[Dict[str, Any]] = None
) -> PRPException:
    """
    Wraps external exceptions (requests, json, etc.) into PRP exceptions.
    
    This provides consistent error handling by converting third-party
    exceptions into our custom PRP exception hierarchy.
    
    Args:
        original_exception: The original exception to wrap
        operation: Description of what operation failed
        context: Additional context about the failure
        
    Returns:
        Appropriate PRPException subclass based on the original exception
        
    Example:
        try:
            response = requests.get(url, timeout=30)
        except requests.exceptions.Timeout as e:
            raise wrap_external_exception(e, "employee details fetch")
    """
    
    context = context or {}
    exception_name = original_exception.__class__.__name__
    message = f"{operation} failed: {str(original_exception)}"
    
    # Map common external exceptions to PRP exceptions
    if 'timeout' in exception_name.lower() or 'connection' in exception_name.lower():
        return PRPConnectionError(
            message=message,
            details={
                'original_exception': exception_name,
                'operation': operation,
                **context
            }
        )
    elif 'auth' in exception_name.lower() or 'unauthorized' in str(original_exception).lower():
        return PRPAuthenticationError(
            message=message,
            details={
                'original_exception': exception_name,
                'operation': operation,
                **context
            }
        )
    elif 'json' in exception_name.lower() or 'decode' in exception_name.lower():
        return PRPDataValidationError(
            message=message,
            details={
                'original_exception': exception_name,
                'operation': operation,
                **context
            }
        )
    else:
        # Generic PRP exception for unhandled external exceptions
        return PRPException(
            message=message,
            error_code="PRP_EXTERNAL_ERROR",
            details={
                'original_exception': exception_name,
                'operation': operation,
                **context
            }
        )


# Exception registry for error code mapping
EXCEPTION_REGISTRY = {
    'PRP_CONNECTION_ERROR': PRPConnectionError,
    'PRP_AUTH_ERROR': PRPAuthenticationError,
    'PRP_SYNC_ERROR': PRPSyncError,
    'PRP_RATE_LIMIT_ERROR': PRPRateLimitError,
    'PRP_DATA_VALIDATION_ERROR': PRPDataValidationError,
    'PRP_CONFIG_ERROR': PRPConfigurationError,
}


def get_exception_class(error_code: str) -> type:
    """
    Get exception class by error code.
    
    Args:
        error_code: The error code to look up
        
    Returns:
        The corresponding exception class
        
    Raises:
        KeyError: If error code not found in registry
    """
    return EXCEPTION_REGISTRY[error_code]


# Export all exception classes for convenient importing
__all__ = [
    'PRPException',
    'PRPConnectionError', 
    'PRPAuthenticationError',
    'PRPSyncError',
    'PRPRateLimitError',
    'PRPDataValidationError',
    'PRPConfigurationError',
    'wrap_external_exception',
    'get_exception_class',
    'EXCEPTION_REGISTRY',
]