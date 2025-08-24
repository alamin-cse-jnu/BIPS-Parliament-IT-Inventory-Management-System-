"""
PRP API Client Module
=====================

Core API client for PRP (Parliament Resource Portal) communication in PIMS
(Parliament IT Inventory Management System).

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Handle PRP API authentication, token management, and data requests

Key Features:
- Token-based authentication with automatic refresh
- Rate limiting and API failure recovery
- Comprehensive logging and error handling
- Secure credential management
- Support for employee and department data retrieval

Dependencies:
- users.api.exceptions (custom PRP exceptions)

API Endpoints (Official PRP API v1.0):
- Authentication: POST /api/authentication/external?action=token
- Token Refresh: GET /api/authentication/external?action=refresh-token
- Employee Details: GET /api/secure/external?action=employee_details&departmentId={departmentId}
- Departments: GET /api/secure/external?action=departments

Usage:
    from users.api.prp_client import PRPClient
    
    client = PRPClient(
        base_url='https://prp.parliament.gov.bd',
        username='ezzetech',
        password='${Fty#3a'
    )
    
    # Get all departments
    departments = client.get_departments()
    
    # Get employees from specific department
    employees = client.get_employee_details(department_id=1)
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from urllib.parse import urljoin
import base64

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from django.conf import settings
from django.utils import timezone

from .exceptions import (
    PRPException,
    PRPConnectionError,
    PRPAuthenticationError,
    PRPSyncError,
    PRPRateLimitError,
    PRPDataValidationError,
    PRPConfigurationError,
    wrap_external_exception
)


# Configure logging for PRP operations
logger = logging.getLogger('pims.prp_integration.client')


@dataclass
class PRPAPIConfig:
    """
    Configuration class for PRP API settings.
    
    Centralizes all PRP API configuration with secure defaults
    and validation for required settings.
    """
    
    # API Connection Settings
    base_url: str = "https://prp.parliament.gov.bd"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    batch_size: int = 50
    rate_limit_delay: float = 0.5
    
    # Authentication Settings (Official PRP API credentials)
    username: str = "ezzetech"
    password: str = "${Fty#3a"
    
    # API Endpoints (from official PRP API v1.0)
    token_endpoint: str = "/api/authentication/external?action=token"
    refresh_endpoint: str = "/api/authentication/external?action=refresh-token"
    employee_details_endpoint: str = "/api/secure/external?action=employee_details&departmentId={departmentId}"
    departments_endpoint: str = "/api/secure/external?action=departments"
    
    # Response validation settings
    success_code: int = 200
    success_message: str = "Success"
    payload_key: str = "payload"
    message_key: str = "msg"
    response_code_key: str = "responseCode"
    
    # Token management
    token_refresh_buffer: int = 300  # Refresh token 5 minutes before expiry
    max_token_refresh_attempts: int = 3
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.base_url:
            raise PRPConfigurationError(
                "PRP_API_BASE_URL is required",
                config_key="base_url"
            )
        
        if not self.username or not self.password:
            raise PRPConfigurationError(
                "PRP API credentials (username/password) are required",
                config_key="credentials"
            )
        
        # Ensure base_url doesn't end with slash
        self.base_url = self.base_url.rstrip('/')


@dataclass
class PRPTokenInfo:
    """
    Container for PRP API token information.
    
    Manages token lifecycle including expiry tracking
    and refresh scheduling.
    """
    
    token: str
    issued_at: datetime
    expires_at: Optional[datetime] = None
    refresh_attempts: int = 0
    
    def __post_init__(self):
        """Initialize token expiry if not provided."""
        if self.expires_at is None:
            # Default token lifetime: 30 minutes (1800 seconds)
            # Based on typical JWT token patterns
            self.expires_at = self.issued_at + timedelta(seconds=1800)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return timezone.now() >= self.expires_at
    
    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (within buffer time)."""
        buffer_time = timezone.now() + timedelta(seconds=300)  # 5 minutes buffer
        return buffer_time >= self.expires_at
    
    @property
    def bearer_token(self) -> str:
        """Get formatted bearer token for API calls."""
        return f"Bearer {self.token}"


class PRPClient:
    """
    Core PRP API client for PIMS integration.
    
    Handles all communication with PRP (Parliament Resource Portal) API
    including authentication, token management, and data retrieval.
    
    Features:
    - Automatic token refresh
    - Rate limiting
    - Comprehensive error handling
    - Request/response logging
    - Connection pooling with retries
    
    Example:
        client = PRPClient()
        departments = client.get_departments()
        employees = client.get_employee_details(department_id=1)
    """
    
    def __init__(
        self, 
        config: Optional[PRPAPIConfig] = None,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize PRP API client.
        
        Args:
            config: Custom configuration object
            base_url: Override default PRP API base URL
            username: Override default username
            password: Override default password
        """
        # Initialize configuration
        if config:
            self.config = config
        else:
            self.config = PRPAPIConfig(
                base_url=base_url or getattr(settings, 'PRP_API_BASE_URL', 'https://prp.parliament.gov.bd'),
                username=username or getattr(settings, 'PRP_USERNAME', 'ezzetech'),
                password=password or getattr(settings, 'PRP_PASSWORD', '${Fty#3a')
            )
        
        # Initialize session with connection pooling and retries
        self.session = self._create_session()
        
        # Token management
        self._token_info: Optional[PRPTokenInfo] = None
        self._token_lock = False
        
        # Rate limiting
        self._last_request_time: Optional[datetime] = None
        
        logger.info(
            f"PRP Client initialized for {self.config.base_url}",
            extra={'username': self.config.username}
        )
    
    def _create_session(self) -> requests.Session:
        """
        Create configured requests session with retries and timeouts.
        
        Returns:
            Configured requests.Session instance
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=self.config.retry_delay,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PIMS-PRP-Integration/1.0',
            'Accept': 'application/json'
        })
        
        return session
    
    def _apply_rate_limiting(self):
        """Apply rate limiting between API requests."""
        if self._last_request_time:
            elapsed = time.time() - self._last_request_time.timestamp()
            if elapsed < self.config.rate_limit_delay:
                sleep_time = self.config.rate_limit_delay - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self._last_request_time = timezone.now()
    
    def _validate_response(self, response_data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """
        Validate PRP API response structure and content.
        
        Args:
            response_data: Raw response data from API
            operation: Description of the operation for error context
            
        Returns:
            Validated response data
            
        Raises:
            PRPDataValidationError: If response format is invalid
        """
        # Check required response structure
        if not isinstance(response_data, dict):
            raise PRPDataValidationError(
                f"Invalid response format for {operation}: expected dict, got {type(response_data)}",
                details={'response_type': str(type(response_data))}
            )
        
        # Validate response code
        response_code = response_data.get(self.config.response_code_key)
        if response_code != self.config.success_code:
            error_msg = response_data.get(self.config.message_key, "Unknown error")
            raise PRPDataValidationError(
                f"{operation} failed with response code {response_code}: {error_msg}",
                details={
                    'response_code': response_code,
                    'error_message': error_msg,
                    'operation': operation
                }
            )
        
        # Validate message
        message = response_data.get(self.config.message_key)
        if message != self.config.success_message:
            logger.warning(
                f"Unexpected response message for {operation}: {message}",
                extra={'expected': self.config.success_message, 'actual': message}
            )
        
        # Extract and validate payload
        payload = response_data.get(self.config.payload_key)
        if payload is None:
            raise PRPDataValidationError(
                f"Missing payload in {operation} response",
                field_name=self.config.payload_key,
                details={'response_keys': list(response_data.keys())}
            )
        
        logger.debug(
            f"Response validated for {operation}",
            extra={
                'response_code': response_code,
                'message': message,
                'payload_type': type(payload).__name__
            }
        )
        
        return response_data
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
        operation: str = "API request"
    ) -> Dict[str, Any]:
        """
        Make HTTP request to PRP API with error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload (for POST requests)
            authenticated: Whether request requires authentication
            operation: Operation description for logging
            
        Returns:
            Parsed JSON response data
            
        Raises:
            PRPConnectionError: On connection issues
            PRPAuthenticationError: On auth failures
            PRPRateLimitError: On rate limiting
            PRPDataValidationError: On invalid responses
        """
        # Apply rate limiting
        self._apply_rate_limiting()
        
        # Prepare request
        url = urljoin(self.config.base_url, endpoint)
        headers = {}
        
        # Add authentication if required
        if authenticated:
            token_info = self._get_valid_token()
            headers['Authorization'] = token_info.bearer_token
        
        logger.debug(
            f"Making {method} request to {url}",
            extra={
                'operation': operation,
                'authenticated': authenticated,
                'has_data': data is not None
            }
        )
        
        try:
            # Make request
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=self.config.timeout
            )
            
            # Handle HTTP errors
            if response.status_code == 401:
                raise PRPAuthenticationError(
                    f"Authentication failed for {operation}",
                    details={'status_code': response.status_code, 'url': url}
                )
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                raise PRPRateLimitError(
                    f"Rate limit exceeded for {operation}",
                    retry_after_seconds=int(retry_after),
                    details={'status_code': response.status_code, 'url': url}
                )
            elif response.status_code >= 400:
                raise PRPConnectionError(
                    f"HTTP {response.status_code} error for {operation}: {response.text}",
                    url=url,
                    details={'status_code': response.status_code, 'response_text': response.text[:500]}
                )
            
            # Parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                raise PRPDataValidationError(
                    f"Invalid JSON response for {operation}",
                    details={'response_text': response.text[:500], 'json_error': str(e)}
                )
            
            # Validate response structure
            validated_response = self._validate_response(response_data, operation)
            
            logger.info(
                f"Successful {method} request to {operation}",
                extra={
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
            )
            
            return validated_response
            
        except requests.exceptions.Timeout as e:
            raise PRPConnectionError(
                f"Timeout connecting to PRP API for {operation}",
                url=url,
                timeout_seconds=self.config.timeout,
                details={'error': str(e)}
            )
        except requests.exceptions.ConnectionError as e:
            raise PRPConnectionError(
                f"Connection error for {operation}",
                url=url,
                details={'error': str(e)}
            )
        except requests.exceptions.RequestException as e:
            raise wrap_external_exception(e, operation, {'url': url})
    
    def _get_valid_token(self) -> PRPTokenInfo:
        """
        Get valid authentication token, refreshing if necessary.
        
        Returns:
            Valid PRPTokenInfo instance
            
        Raises:
            PRPAuthenticationError: If token acquisition/refresh fails
        """
        # Check if we need to acquire initial token
        if not self._token_info or self._token_info.is_expired:
            logger.info("Acquiring new PRP authentication token")
            self._acquire_token()
        # Check if token needs refresh
        elif self._token_info.needs_refresh:
            logger.info("Refreshing PRP authentication token")
            self._refresh_token()
        
        return self._token_info
    
    def _acquire_token(self):
        """
        Acquire new authentication token from PRP API.
        
        Raises:
            PRPAuthenticationError: If token acquisition fails
        """
        if self._token_lock:
            # Prevent concurrent token requests
            time.sleep(1)
            if self._token_info and not self._token_info.is_expired:
                return
        
        self._token_lock = True
        
        try:
            logger.info(
                f"Requesting new token for user: {self.config.username}",
                extra={'endpoint': self.config.token_endpoint}
            )
            
            response_data = self._make_request(
                method="POST",
                endpoint=self.config.token_endpoint,
                data={
                    "username": self.config.username,
                    "password": self.config.password
                },
                authenticated=False,
                operation="token acquisition"
            )
            
            # Extract token from response
            token = response_data[self.config.payload_key]
            if not token or not isinstance(token, str):
                raise PRPAuthenticationError(
                    "Invalid token format in authentication response",
                    auth_step="token_extraction",
                    details={'token_type': type(token).__name__}
                )
            
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Create token info
            self._token_info = PRPTokenInfo(
                token=token,
                issued_at=timezone.now()
            )
            
            logger.info(
                "Successfully acquired PRP authentication token",
                extra={
                    'expires_at': self._token_info.expires_at.isoformat(),
                    'token_length': len(token)
                }
            )
            
        except PRPException:
            raise
        except Exception as e:
            raise PRPAuthenticationError(
                f"Token acquisition failed: {str(e)}",
                auth_step="token_request",
                username=self.config.username,
                details={'error': str(e)}
            )
        finally:
            self._token_lock = False
    
    def _refresh_token(self):
        """
        Refresh existing authentication token.
        
        Raises:
            PRPAuthenticationError: If token refresh fails
        """
        if not self._token_info:
            self._acquire_token()
            return
        
        if self._token_info.refresh_attempts >= self.config.max_token_refresh_attempts:
            logger.warning("Maximum token refresh attempts exceeded, acquiring new token")
            self._acquire_token()
            return
        
        try:
            logger.info("Refreshing PRP authentication token")
            
            response_data = self._make_request(
                method="GET",
                endpoint=self.config.refresh_endpoint,
                authenticated=True,
                operation="token refresh"
            )
            
            # Extract refreshed token
            token = response_data[self.config.payload_key]
            if not token or not isinstance(token, str):
                raise PRPAuthenticationError(
                    "Invalid token format in refresh response",
                    auth_step="token_refresh",
                    details={'token_type': type(token).__name__}
                )
            
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Update token info
            self._token_info.token = token
            self._token_info.issued_at = timezone.now()
            self._token_info.expires_at = timezone.now() + timedelta(seconds=1800)
            self._token_info.refresh_attempts += 1
            
            logger.info(
                "Successfully refreshed PRP authentication token",
                extra={
                    'expires_at': self._token_info.expires_at.isoformat(),
                    'refresh_attempt': self._token_info.refresh_attempts
                }
            )
            
        except PRPAuthenticationError:
            logger.warning("Token refresh failed, acquiring new token")
            self._acquire_token()
        except Exception as e:
            raise PRPAuthenticationError(
                f"Token refresh failed: {str(e)}",
                auth_step="token_refresh",
                details={'error': str(e)}
            )
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """
        Retrieve all departments from PRP API.
        
        Returns list of department objects with structure:
        {
            "nameEng": "Department Name English",
            "nameBng": "Department Name Bengali", 
            "id": 1,
            "isWing": false
        }
        
        Returns:
            List of department dictionaries
            
        Raises:
            PRPException: On API communication errors
        """
        logger.info("Fetching departments from PRP API")
        
        response_data = self._make_request(
            method="GET",
            endpoint=self.config.departments_endpoint,
            operation="get departments"
        )
        
        departments = response_data[self.config.payload_key]
        
        # Validate departments structure
        if not isinstance(departments, list):
            raise PRPDataValidationError(
                "Departments payload must be a list",
                expected_type="list",
                actual_value=type(departments).__name__
            )
        
        logger.info(
            f"Successfully retrieved {len(departments)} departments",
            extra={'department_count': len(departments)}
        )
        
        return departments
    
    def get_employee_details(self, department_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve employee details for a specific department.
        
        Returns list of employee objects with structure (PIMS uses only these fields):
        {
            "userId": "12345",
            "nameEng": "Full Name English",
            "designationEng": "Designation English",
            "email": "user@parliament.gov.bd",
            "mobile": "01700000000",
            "photo": byte_array_data,
            "status": "active"
        }
        
        Args:
            department_id: ID of the department to retrieve employees for
            
        Returns:
            List of employee dictionaries
            
        Raises:
            PRPException: On API communication errors
        """
        if not isinstance(department_id, int) or department_id <= 0:
            raise PRPDataValidationError(
                f"Department ID must be a positive integer, got: {department_id}",
                field_name="department_id",
                expected_type="positive integer",
                actual_value=department_id
            )
        
        logger.info(
            f"Fetching employee details for department ID: {department_id}",
            extra={'department_id': department_id}
        )
        
        endpoint = self.config.employee_details_endpoint.format(departmentId=department_id)
        
        response_data = self._make_request(
            method="GET",
            endpoint=endpoint,
            operation=f"get employee details for department {department_id}"
        )
        
        employees = response_data[self.config.payload_key]
        
        # Validate employees structure
        if not isinstance(employees, list):
            raise PRPDataValidationError(
                "Employee details payload must be a list",
                expected_type="list",
                actual_value=type(employees).__name__,
                details={'department_id': department_id}
            )
        
        logger.info(
            f"Successfully retrieved {len(employees)} employees for department {department_id}",
            extra={'employee_count': len(employees), 'department_id': department_id}
        )
        
        return employees
    
    def validate_employee_data(self, employee: Dict[str, Any]) -> bool:
        """
        Validate employee data structure for PIMS integration.
        
        Checks that required fields are present and have valid types.
        PIMS only uses: userId, nameEng, designationEng, email, mobile, photo, status
        
        Args:
            employee: Employee data dictionary to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            PRPDataValidationError: If critical fields are invalid
        """
        required_fields = ['userId', 'nameEng', 'email']
        optional_fields = ['designationEng', 'mobile', 'photo', 'status']
        
        # Check required fields
        for field in required_fields:
            if field not in employee:
                raise PRPDataValidationError(
                    f"Missing required field: {field}",
                    field_name=field,
                    details={'employee_data_keys': list(employee.keys())}
                )
            
            if not employee[field]:
                raise PRPDataValidationError(
                    f"Required field {field} cannot be empty",
                    field_name=field,
                    actual_value=employee[field]
                )
        
        # Validate field types
        if not isinstance(employee['userId'], str):
            raise PRPDataValidationError(
                "userId must be a string",
                field_name="userId",
                expected_type="string",
                actual_value=employee['userId']
            )
        
        if employee.get('email') and '@' not in str(employee['email']):
            logger.warning(
                f"Invalid email format for user {employee['userId']}: {employee['email']}",
                extra={'user_id': employee['userId'], 'email': employee['email']}
            )
        
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test PRP API connection and authentication.
        
        Returns:
            Dictionary with connection test results
        """
        test_result = {
            'success': False,
            'timestamp': timezone.now().isoformat(),
            'base_url': self.config.base_url,
            'username': self.config.username,
            'tests': {}
        }
        
        try:
            # Test 1: Token acquisition
            logger.info("Testing PRP API connection...")
            self._acquire_token()
            test_result['tests']['authentication'] = {
                'success': True,
                'message': 'Token acquired successfully'
            }
            
            # Test 2: Departments endpoint
            try:
                departments = self.get_departments()
                test_result['tests']['departments_endpoint'] = {
                    'success': True,
                    'message': f'Retrieved {len(departments)} departments'
                }
            except Exception as e:
                test_result['tests']['departments_endpoint'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Test 3: Employee details endpoint (with first department if available)
            try:
                departments = self.get_departments()
                if departments:
                    dept_id = departments[0]['id']
                    employees = self.get_employee_details(dept_id)
                    test_result['tests']['employee_details_endpoint'] = {
                        'success': True,
                        'message': f'Retrieved {len(employees)} employees from department {dept_id}'
                    }
                else:
                    test_result['tests']['employee_details_endpoint'] = {
                        'success': False,
                        'message': 'No departments available for testing'
                    }
            except Exception as e:
                test_result['tests']['employee_details_endpoint'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Overall success if authentication worked
            test_result['success'] = test_result['tests']['authentication']['success']
            
        except Exception as e:
            test_result['tests']['authentication'] = {
                'success': False,
                'error': str(e)
            }
            test_result['error'] = str(e)
        
        logger.info(
            f"PRP API connection test completed: {'SUCCESS' if test_result['success'] else 'FAILURE'}",
            extra=test_result
        )
        
        return test_result
    
    def close(self):
        """Close the client session and cleanup resources."""
        if self.session:
            self.session.close()
            logger.info("PRP Client session closed")


# Convenience function for creating configured client
def create_prp_client(
    base_url: Optional[str] = None,
    username: Optional[str] = None, 
    password: Optional[str] = None
) -> PRPClient:
    """
    Create a configured PRP client instance.
    
    Args:
        base_url: PRP API base URL (defaults to settings or hardcoded)
        username: PRP username (defaults to settings or hardcoded)
        password: PRP password (defaults to settings or hardcoded)
        
    Returns:
        Configured PRPClient instance
        
    Example:
        client = create_prp_client()
        departments = client.get_departments()
    """
    return PRPClient(
        base_url=base_url,
        username=username,
        password=password
    )


# Export classes and functions
__all__ = [
    'PRPClient',
    'PRPAPIConfig', 
    'PRPTokenInfo',
    'create_prp_client',
]