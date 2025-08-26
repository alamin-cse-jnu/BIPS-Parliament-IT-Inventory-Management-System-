"""
Custom Exceptions for PRP (Parliament Resource Portal) Integration
================================================================

This module defines custom exceptions for PRP API operations in PIMS
(Parliament IT Inventory Management System).

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Comprehensive error handling for real PRP API integration

Based on Official PRP Integration Requirements:
- API Base URL: https://prp.parliament.gov.bd
- Authentication: Bearer token (username: "ezzetech", password: "${Fty#3a")
- Business Rules: One-way sync PRP → PIMS, admin-controlled operations
- Data Models: EmployeeDetails, DepartmentModel
- Response Format: {responseCode: 200, payload: [...], msg: "Success"}

Exception Hierarchy:
-------------------
PRPException (Base)
├── PRPConnectionError (Network/HTTP issues)
├── PRPAuthenticationError (Token/auth failures)  
├── PRPSyncError (Data synchronization failures)
├── PRPRateLimitError (API rate limiting)
├── PRPDataValidationError (Invalid response data)
├── PRPConfigurationError (Setup/config issues)
└── PRPBusinessRuleError (Business logic violations)

Usage Example:
-------------
from users.api.exceptions import PRPConnectionError, PRPAuthenticationError

try:
    result = prp_client.get_department_employees(department_id=1)
except PRPAuthenticationError as e:
    logger.error(f"PRP authentication failed: {e}")
    # Handle auth failure (refresh token, etc.)
except PRPConnectionError as e:  
    logger.error(f"PRP connection error: {e}")
    # Handle connection failure (retry, check network, etc.)
except PRPDataValidationError as e:
    logger.error(f"Invalid PRP data: {e}")
    # Handle data validation issues
"""

import logging
from typing import Optional, Dict, Any, Union
from django.utils import timezone

# Configure logging for PRP exceptions
logger = logging.getLogger('pims.prp_integration.exceptions')


class PRPException(Exception):
    """
    Base exception class for all PRP API related errors.
    
    All PRP-specific exceptions inherit from this class to provide
    consistent error handling across the PIMS-PRP integration.
    
    Features:
    - Structured error information (message, code, details)
    - Automatic logging of errors
    - Bangladesh Parliament Secretariat context
    - Integration with Django logging system
    
    Attributes:
        message (str): Human-readable error message
        error_code (str): Internal error code for logging/tracking
        details (dict): Additional error context/details
        timestamp (datetime): When the error occurred (Asia/Dhaka timezone)
        location (str): Fixed location context for Parliament Secretariat
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "PRP_ERROR",
        details: Optional[Dict[str, Any]] = None,
        log_level: str = "error"
    ):
        """
        Initialize PRP exception with structured error information.
        
        Args:
            message: Human-readable error message
            error_code: Internal error code for categorization
            details: Additional error context dictionary
            log_level: Logging level ("error", "warning", "info")
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = timezone.now()
        self.location = "Bangladesh Parliament Secretariat, Dhaka"
        
        # Add common context to details
        self.details.update({
            'timestamp': self.timestamp.isoformat(),
            'location': self.location,
            'exception_type': self.__class__.__name__
        })
        
        # Log the exception when created
        log_method = getattr(logger, log_level, logger.error)
        log_method(
            f"PRP Exception [{self.error_code}]: {message}",
            extra={
                'error_code': self.error_code,
                'exception_type': self.__class__.__name__,
                'details': self.details,
                'location': self.location
            }
        )
    
    def __str__(self) -> str:
        """Return string representation of the exception."""
        return f"[{self.error_code}] {self.message}"
    
    def __repr__(self) -> str:
        """Return detailed representation of the exception."""
        return f"{self.__class__.__name__}('{self.message}', error_code='{self.error_code}')"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses and logging.
        
        Returns:
            dict: Exception data as dictionary
        """
        return {
            'exception_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'timestamp': self.timestamp.isoformat(),
            'location': self.location,
            'details': self.details
        }
    
    def get_user_friendly_message(self) -> str:
        """
        Get user-friendly error message for display in templates.
        
        Returns:
            str: User-friendly error message
        """
        return self.message


class PRPConnectionError(PRPException):
    """
    Raised when connection to PRP API fails.
    
    This covers network timeouts, DNS resolution failures, 
    connection refused, SSL/TLS issues, and other HTTP-level connection problems.
    
    Business Impact: Prevents all PRP operations until connection restored
    Recovery Actions: 
    - Retry with exponential backoff
    - Check network connectivity
    - Verify PRP API status
    - Check firewall/proxy settings
    
    Common Scenarios:
    - Network timeout connecting to https://prp.parliament.gov.bd
    - DNS resolution failure for PRP domain
    - Connection refused (PRP server down/maintenance)
    - SSL/TLS handshake failures
    - Proxy authentication failures
    """
    
    def __init__(
        self, 
        message: str = "Failed to connect to PRP API", 
        url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize connection error with network context.
        
        Args:
            message: Error description
            url: The URL that failed
            timeout_seconds: Timeout value used
            status_code: HTTP status code if available
            details: Additional error context
        """
        error_details = details or {}
        if url:
            error_details['url'] = url
        if timeout_seconds:
            error_details['timeout_seconds'] = timeout_seconds
        if status_code:
            error_details['http_status_code'] = status_code
            
        super().__init__(
            message=message,
            error_code="PRP_CONNECTION_ERROR", 
            details=error_details,
            log_level="warning"  # Connection issues are warnings, not critical errors
        )
    
    def get_user_friendly_message(self) -> str:
        """Get user-friendly message for connection errors."""
        return "Unable to connect to Parliament Resource Portal. Please check your internet connection or try again later."


class PRPAuthenticationError(PRPException):
    """
    Raised when PRP API authentication fails.
    
    This covers token acquisition failures, token refresh failures,
    invalid credentials, expired tokens, and authorization issues.
    
    Business Impact: Blocks all PRP operations until authentication resolved
    Recovery Actions:
    - Verify PRP credentials (username: "ezzetech", password: "${Fty#3a")
    - Refresh authentication tokens
    - Check account status with PRP administrators
    - Verify API permissions
    
    Common Scenarios:
    - Invalid username/password for token acquisition
    - Expired bearer token requiring refresh
    - Token refresh API failure
    - Account locked/disabled in PRP system
    - Insufficient API permissions
    """
    
    def __init__(
        self, 
        message: str = "PRP authentication failed",
        auth_step: Optional[str] = None,
        username: Optional[str] = None,
        token_expired: Optional[bool] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize authentication error with auth context.
        
        Args:
            message: Error description
            auth_step: Which authentication step failed
            username: Username used (for logging, not password)
            token_expired: Whether token expiry was the cause
            details: Additional error context
        """
        error_details = details or {}
        if auth_step:
            error_details['auth_step'] = auth_step
        if username:
            # Log username but never log password for security
            error_details['username'] = username
        if token_expired is not None:
            error_details['token_expired'] = token_expired
            
        super().__init__(
            message=message,
            error_code="PRP_AUTH_ERROR",
            details=error_details,
            log_level="error"  # Auth failures are serious security events
        )
    
    def get_user_friendly_message(self) -> str:
        """Get user-friendly message for auth errors."""
        return "Authentication with Parliament Resource Portal failed. Please contact the system administrator."


class PRPSyncError(PRPException):
    """
    Raised when user data synchronization from PRP fails.
    
    This covers data mapping failures, database update errors,
    business rule violations, and sync state inconsistencies.
    
    Business Impact: User data may be stale or inconsistent between PRP and PIMS
    Recovery Actions:
    - Retry sync operation
    - Validate data mappings (PRP → PIMS field mapping)
    - Check database constraints
    - Verify business rule compliance
    - Manual data validation may be required
    
    Common Scenarios:
    - Failed to map PRP userId to PIMS employee_id
    - Department not found for PRP employee
    - Database constraint violation during user creation/update
    - Status mapping conflicts (PRP active vs PIMS admin override inactive)
    - Photo conversion/upload failures
    """
    
    def __init__(
        self, 
        message: str = "PRP user sync failed",
        sync_operation: Optional[str] = None,
        user_id: Optional[str] = None,
        department_id: Optional[int] = None,
        field_mapping_error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize sync error with synchronization context.
        
        Args:
            message: Error description
            sync_operation: Type of sync operation that failed
            user_id: PRP userId being synced
            department_id: Department ID being processed
            field_mapping_error: Specific field mapping issue
            details: Additional error context
        """
        error_details = details or {}
        if sync_operation:
            error_details['sync_operation'] = sync_operation
        if user_id:
            error_details['user_id'] = user_id
        if department_id:
            error_details['department_id'] = department_id
        if field_mapping_error:
            error_details['field_mapping_error'] = field_mapping_error
            
        super().__init__(
            message=message,
            error_code="PRP_SYNC_ERROR",
            details=error_details,
            log_level="error"  # Sync failures require immediate attention
        )
    
    def get_user_friendly_message(self) -> str:
        """Get user-friendly message for sync errors."""
        return "Failed to synchronize user data from Parliament Resource Portal. Some user information may be outdated."


class PRPRateLimitError(PRPException):
    """
    Raised when PRP API rate limits are exceeded.
    
    PRP API may have request limits per minute/hour to prevent abuse.
    This exception handles rate limiting scenarios and provides retry guidance.
    
    Business Impact: Temporary delay in sync operations
    Recovery Actions:
    - Wait for rate limit reset period
    - Implement exponential backoff retry strategy
    - Reduce concurrent API requests
    - Consider batching API calls more efficiently
    
    Common Scenarios:
    - Exceeded 100 requests per minute limit
    - Concurrent sync operations hitting limits
    - Bulk department sync triggering rate limits
    - Multiple admin users running sync simultaneously
    """
    
    def __init__(
        self, 
        message: str = "PRP API rate limit exceeded",
        retry_after_seconds: Optional[int] = None,
        request_count: Optional[int] = None,
        limit_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize rate limit error with retry context.
        
        Args:
            message: Error description
            retry_after_seconds: How long to wait before retrying
            request_count: Number of requests that triggered limit
            limit_type: Type of rate limit (per minute, per hour, etc.)
            details: Additional error context
        """
        error_details = details or {}
        if retry_after_seconds:
            error_details['retry_after_seconds'] = retry_after_seconds
        if request_count:
            error_details['request_count'] = request_count
        if limit_type:
            error_details['limit_type'] = limit_type
            
        super().__init__(
            message=message,
            error_code="PRP_RATE_LIMIT_ERROR",
            details=error_details,
            log_level="warning"  # Rate limits are expected, not errors
        )
    
    def get_user_friendly_message(self) -> str:
        """Get user-friendly message for rate limit errors."""
        retry_time = self.details.get('retry_after_seconds', 60)
        return f"Parliament Resource Portal is busy. Please wait {retry_time} seconds before trying again."


class PRPDataValidationError(PRPException):
    """
    Raised when PRP API returns invalid or unexpected data.
    
    This covers malformed JSON responses, missing required fields,
    invalid data types, and schema validation failures.
    
    Business Impact: Cannot process PRP data for sync operations
    Recovery Actions:
    - Check PRP API response format
    - Validate data schema assumptions
    - Handle missing fields gracefully
    - Report data format issues to PRP administrators
    
    Common Scenarios:
    - Missing required 'userId' field in EmployeeDetails
    - Invalid email format in PRP response
    - Null values for required fields (nameEng, designationEng)
    - Response schema changes in PRP API
    - Photo data corruption (invalid byte array)
    """
    
    def __init__(
        self, 
        message: str = "Invalid data received from PRP API",
        field_name: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize data validation error with field context.
        
        Args:
            message: Error description
            field_name: Name of the field that failed validation
            expected_type: Expected data type or format
            actual_value: Actual value received (sanitized)
            validation_rule: Which validation rule failed
            details: Additional error context
        """
        error_details = details or {}
        if field_name:
            error_details['field_name'] = field_name
        if expected_type:
            error_details['expected_type'] = expected_type
        if actual_value is not None:
            # Sanitize actual value for logging (truncate if too long)
            sanitized_value = str(actual_value)
            if len(sanitized_value) > 200:
                sanitized_value = sanitized_value[:200] + "... (truncated)"
            error_details['actual_value'] = sanitized_value
        if validation_rule:
            error_details['validation_rule'] = validation_rule
            
        super().__init__(
            message=message,
            error_code="PRP_DATA_VALIDATION_ERROR",
            details=error_details,
            log_level="error"  # Data validation issues need investigation
        )
    
    def get_user_friendly_message(self) -> str:
        """Get user-friendly message for data validation errors."""
        return "Received invalid data from Parliament Resource Portal. Please contact the system administrator."


class PRPConfigurationError(PRPException):
    """
    Raised when PRP integration configuration is invalid.
    
    This covers missing Django settings, invalid URLs, credential issues,
    and other configuration-related problems.
    
    Business Impact: Prevents PRP integration from functioning
    Recovery Actions:
    - Check Django settings.py for PRP configuration
    - Verify PRP_BASE_URL, PRP_USERNAME, PRP_PASSWORD settings
    - Check environment variables
    - Validate configuration against requirements
    
    Common Scenarios:
    - Missing PRP_BASE_URL in Django settings
    - Invalid PRP API credentials in settings
    - Missing required environment variables
    - Incorrect API endpoint URLs
    - Invalid timeout/retry configuration
    """
    
    def __init__(
        self, 
        message: str = "PRP integration configuration error",
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
        expected_format: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize configuration error with config context.
        
        Args:
            message: Error description
            config_key: Configuration key that's invalid
            config_value: Configuration value (sanitized)
            expected_format: Expected format or value
            details: Additional error context
        """
        error_details = details or {}
        if config_key:
            error_details['config_key'] = config_key
        if config_value:
            # Sanitize config value (don't log passwords)
            if 'password' in config_key.lower() or 'secret' in config_key.lower():
                error_details['config_value'] = "[REDACTED]"
            else:
                error_details['config_value'] = str(config_value)
        if expected_format:
            error_details['expected_format'] = expected_format
            
        super().__init__(
            message=message,
            error_code="PRP_CONFIG_ERROR",
            details=error_details,
            log_level="error"  # Config issues prevent system operation
        )
    
    def get_user_friendly_message(self) -> str:
        """Get user-friendly message for config errors."""
        return "Parliament Resource Portal integration is not properly configured. Please contact the system administrator."


class PRPBusinessRuleError(PRPException):
    """
    Raised when PRP business rule violations occur.
    
    This handles violations of PIMS-PRP integration business rules
    such as attempting to edit PRP-managed fields, violating one-way sync rules, etc.
    
    Business Impact: Prevents operations that would violate business logic
    Recovery Actions:
    - Review business rule requirements
    - Check admin permissions
    - Validate operation against PRP integration rules
    
    Business Rules (from Integration Context):
    1. User Creation: NO user creation from PIMS interface
    2. Data Authority: PRP is the single source of truth  
    3. Sync Direction: One-way PRP → PIMS only
    4. Field Editing: PRP-sourced fields are read-only in PIMS
    5. Status Override: PIMS admin can override user status
    6. Sync Control: Admin-initiated sync operations only
    """
    
    def __init__(
        self, 
        message: str = "PRP business rule violation",
        rule_name: Optional[str] = None,
        attempted_operation: Optional[str] = None,
        user_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize business rule error with rule context.
        
        Args:
            message: Error description
            rule_name: Name of the business rule violated
            attempted_operation: Operation that was attempted
            user_role: Role of user attempting operation
            details: Additional error context
        """
        error_details = details or {}
        if rule_name:
            error_details['rule_name'] = rule_name
        if attempted_operation:
            error_details['attempted_operation'] = attempted_operation
        if user_role:
            error_details['user_role'] = user_role
            
        super().__init__(
            message=message,
            error_code="PRP_BUSINESS_RULE_ERROR",
            details=error_details,
            log_level="warning"  # Business rule violations are expected user behavior
        )
    
    def get_user_friendly_message(self) -> str:
        """Get user-friendly message for business rule errors."""
        return "This operation is not allowed. Parliament Resource Portal data can only be modified by administrators."


def wrap_external_exception(
    original_exception: Exception, 
    operation: str,
    context: Optional[Dict[str, Any]] = None
) -> PRPException:
    """
    Wrap external exceptions (requests, JSON, etc.) into PRP exceptions.
    
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
            raise wrap_external_exception(e, "employee details fetch", {'url': url})
    """
    context = context or {}
    exception_name = original_exception.__class__.__name__
    original_message = str(original_exception)
    message = f"{operation} failed: {original_message}"
    
    # Add original exception details to context
    context.update({
        'original_exception': exception_name,
        'original_message': original_message,
        'operation': operation
    })
    
    # Map common external exceptions to appropriate PRP exceptions
    if any(keyword in exception_name.lower() for keyword in ['timeout', 'connection', 'network']):
        return PRPConnectionError(
            message=message,
            details=context
        )
    elif any(keyword in exception_name.lower() for keyword in ['auth', 'unauthorized', 'forbidden']):
        return PRPAuthenticationError(
            message=message,
            details=context
        )
    elif any(keyword in exception_name.lower() for keyword in ['json', 'decode', 'parse']):
        return PRPDataValidationError(
            message=message,
            details=context
        )
    elif 'rate' in exception_name.lower() or 'limit' in exception_name.lower():
        return PRPRateLimitError(
            message=message,
            details=context
        )
    else:
        # Generic PRP exception for unhandled external exceptions
        return PRPException(
            message=message,
            error_code="PRP_EXTERNAL_ERROR",
            details=context
        )


# Exception registry for error code mapping and reverse lookups
EXCEPTION_REGISTRY = {
    'PRP_CONNECTION_ERROR': PRPConnectionError,
    'PRP_AUTH_ERROR': PRPAuthenticationError,
    'PRP_SYNC_ERROR': PRPSyncError,
    'PRP_RATE_LIMIT_ERROR': PRPRateLimitError,
    'PRP_DATA_VALIDATION_ERROR': PRPDataValidationError,
    'PRP_CONFIG_ERROR': PRPConfigurationError,
    'PRP_BUSINESS_RULE_ERROR': PRPBusinessRuleError,
    'PRP_ERROR': PRPException,
}


def get_exception_class(error_code: str) -> type:
    """
    Get exception class by error code.
    
    Args:
        error_code: Error code string
        
    Returns:
        Exception class corresponding to the error code
        
    Example:
        exception_class = get_exception_class('PRP_AUTH_ERROR')
        # Returns PRPAuthenticationError
    """
    return EXCEPTION_REGISTRY.get(error_code, PRPException)


def create_exception_from_code(
    error_code: str, 
    message: str, 
    **kwargs
) -> PRPException:
    """
    Create exception instance from error code and message.
    
    Args:
        error_code: Error code string
        message: Error message
        **kwargs: Additional arguments for exception constructor
        
    Returns:
        Exception instance of the appropriate type
        
    Example:
        exc = create_exception_from_code(
            'PRP_AUTH_ERROR', 
            'Token expired',
            auth_step='token_validation'
        )
    """
    exception_class = get_exception_class(error_code)
    return exception_class(message, **kwargs)


# Export all exception classes for easy importing
__all__ = [
    'PRPException',
    'PRPConnectionError',
    'PRPAuthenticationError', 
    'PRPSyncError',
    'PRPRateLimitError',
    'PRPDataValidationError',
    'PRPConfigurationError',
    'PRPBusinessRuleError',
    'wrap_external_exception',
    'get_exception_class',
    'create_exception_from_code',
    'EXCEPTION_REGISTRY'
]