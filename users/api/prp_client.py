"""
PRP API Client Module
=====================

Core API client for PRP (Parliament Resource Portal) communication in PIMS
(Parliament IT Inventory Management System).

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Handle PRP API authentication, token management, and data requests

Template Design Pattern: Flat Design, High Contrast (NO glassmorphism)
Color Scheme: Teal (#28a745), Orange (#fd7e14), Red (#dc3545)
Timezone: Asia/Dhaka (Bangladesh Parliament Secretariat)

Key Features:
- Token-based authentication with automatic refresh
- Rate limiting and API failure recovery
- Comprehensive logging and error handling
- Secure credential management for Bangladesh Parliament
- Support for employee and department data retrieval
- Asia/Dhaka timezone consistency

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
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from urllib.parse import urljoin
import base64

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings
from django.utils import timezone

from .exceptions import (
    PRPBaseException,
    PRPConnectionError,
    PRPAuthenticationError,
    PRPSyncError,
    PRPRateLimitError,
    PRPDataValidationError,
    PRPConfigurationError,
    wrap_external_exception
)

# Configure timezone for Bangladesh Parliament Secretariat
BD_TIMEZONE = pytz.timezone('Asia/Dhaka')

# Configure logging for PRP operations
logger = logging.getLogger('pims.prp_integration.client')


@dataclass
class PRPAPIConfig:
    """
    Configuration class for PRP API settings.
    
    Centralizes all PRP API configuration with secure defaults
    and validation for required settings for Bangladesh Parliament Secretariat.
    
    Template Design Pattern: Simple, functional configuration
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    """
    
    # API Connection Settings (Bangladesh Parliament specific)
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
                "PRP_API_BASE_URL is required for Bangladesh Parliament integration",
                config_key="base_url"
            )
        
        if not self.username or not self.password:
            raise PRPConfigurationError(
                "PRP API credentials (username/password) are required for Parliament authentication",
                config_key="credentials"
            )
        
        # Ensure base_url doesn't end with slash
        self.base_url = self.base_url.rstrip('/')


@dataclass
class PRPTokenInfo:
    """
    Container for PRP API token information.
    
    Manages token lifecycle including expiry tracking
    and refresh scheduling for Bangladesh Parliament operations.
    """
    
    token: str
    issued_at: datetime
    expires_at: Optional[datetime] = None
    refresh_attempts: int = 0
    
    def __post_init__(self):
        """Initialize token expiry if not provided."""
        if self.expires_at is None:
            # Default token lifetime: 30 minutes (1800 seconds)
            # Based on typical JWT token patterns for government systems
            self.expires_at = self.issued_at + timedelta(seconds=1800)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired (Bangladesh time)."""
        current_time = timezone.now()
        if timezone.is_naive(current_time):
            current_time = BD_TIMEZONE.localize(current_time)
        return current_time >= self.expires_at
    
    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (within buffer time)."""
        current_time = timezone.now()
        if timezone.is_naive(current_time):
            current_time = BD_TIMEZONE.localize(current_time)
        buffer_time = current_time + timedelta(seconds=300)  # 5 minutes buffer
        return buffer_time >= self.expires_at
    
    @property
    def bearer_token(self) -> str:
        """Get formatted bearer token for API calls."""
        return f"Bearer {self.token}"


class PRPClient:
    """
    Core PRP API client for PIMS integration at Bangladesh Parliament Secretariat.
    
    Handles all communication with PRP (Parliament Resource Portal) API
    including authentication, token management, and data retrieval.
    
    Features:
    - Automatic token refresh with Bangladesh timezone handling
    - Rate limiting appropriate for government systems
    - Comprehensive error handling and logging
    - Request/response logging for audit trails
    - Connection pooling with retries
    - Template design consistency (flat design, high contrast)
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    
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
        Initialize PRP API client for Bangladesh Parliament Secretariat.
        
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
            f"PRP Client initialized for Bangladesh Parliament Secretariat, Dhaka",
            extra={
                'base_url': self.config.base_url,
                'username': self.config.username,
                'location': 'Bangladesh Parliament Secretariat, Dhaka',
                'timezone': 'Asia/Dhaka'
            }
        )
    
    def _create_session(self) -> requests.Session:
        """
        Create configured requests session with retries and timeouts.
        
        Returns:
            Configured requests.Session instance for Bangladesh Parliament operations
        """
        session = requests.Session()
        
        # Configure retry strategy for government network reliability
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
        
        # Set default headers with Bangladesh Parliament identification
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PIMS-PRP-Integration-BD-Parliament/1.0',
            'Accept': 'application/json',
            'X-Location': 'Dhaka-Bangladesh',
            'X-Client': 'Bangladesh-Parliament-Secretariat'
        })
        
        return session
    
    def _apply_rate_limiting(self):
        """Apply rate limiting between API requests (government-appropriate)."""
        if self._last_request_time:
            current_time = timezone.now()
            if timezone.is_naive(current_time):
                current_time = BD_TIMEZONE.localize(current_time)
            
            elapsed = (current_time - self._last_request_time).total_seconds()
            if elapsed < self.config.rate_limit_delay:
                sleep_time = self.config.rate_limit_delay - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for Parliament API")
                time.sleep(sleep_time)
        
        current_time = timezone.now()
        if timezone.is_naive(current_time):
            current_time = BD_TIMEZONE.localize(current_time)
        self._last_request_time = current_time
    
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
                f"Invalid response format for {operation} from Bangladesh Parliament PRP: expected dict, got {type(response_data)}",
                details={'response_type': str(type(response_data)), 'location': 'Bangladesh Parliament Secretariat'}
            )
        
        # Validate response code
        response_code = response_data.get(self.config.response_code_key)
        if response_code != self.config.success_code:
            error_msg = response_data.get(self.config.message_key, "Unknown error")
            raise PRPDataValidationError(
                f"{operation} failed at Bangladesh Parliament PRP with response code {response_code}: {error_msg}",
                details={
                    'response_code': response_code,
                    'error_message': error_msg,
                    'operation': operation,
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
        
        # Validate message
        message = response_data.get(self.config.message_key)
        if message != self.config.success_message:
            logger.warning(
                f"Unexpected response message for {operation} from Parliament PRP: {message}",
                extra={
                    'expected': self.config.success_message, 
                    'actual': message,
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
        
        # Extract and validate payload
        payload = response_data.get(self.config.payload_key)
        if payload is None:
            raise PRPDataValidationError(
                f"Missing payload in {operation} response from Bangladesh Parliament PRP",
                field_name=self.config.payload_key,
                details={
                    'response_keys': list(response_data.keys()),
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
        
        logger.debug(
            f"Response validated for {operation} at Bangladesh Parliament",
            extra={
                'response_code': response_code,
                'message': message,
                'payload_type': type(payload).__name__,
                'location': 'Bangladesh Parliament Secretariat'
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
            f"Making {method} request to Bangladesh Parliament PRP: {url}",
            extra={
                'operation': operation,
                'authenticated': authenticated,
                'has_data': data is not None,
                'location': 'Bangladesh Parliament Secretariat'
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
            
            # Handle HTTP errors with Bangladesh Parliament context
            if response.status_code == 401:
                raise PRPAuthenticationError(
                    f"Authentication failed for {operation} at Bangladesh Parliament PRP",
                    details={
                        'status_code': response.status_code, 
                        'url': url,
                        'location': 'Bangladesh Parliament Secretariat'
                    }
                )
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                raise PRPRateLimitError(
                    f"Rate limit exceeded for {operation} at Bangladesh Parliament PRP",
                    retry_after_seconds=int(retry_after),
                    details={
                        'status_code': response.status_code, 
                        'url': url,
                        'location': 'Bangladesh Parliament Secretariat'
                    }
                )
            elif response.status_code >= 400:
                raise PRPConnectionError(
                    f"HTTP {response.status_code} error for {operation} at Bangladesh Parliament PRP: {response.text[:200]}",
                    url=url,
                    details={
                        'status_code': response.status_code, 
                        'response_text': response.text[:500],
                        'location': 'Bangladesh Parliament Secretariat'
                    }
                )
            
            # Parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                raise PRPDataValidationError(
                    f"Invalid JSON response for {operation} from Bangladesh Parliament PRP",
                    details={
                        'response_text': response.text[:500], 
                        'json_error': str(e),
                        'location': 'Bangladesh Parliament Secretariat'
                    }
                )
            
            # Validate response structure
            validated_response = self._validate_response(response_data, operation)
            
            logger.info(
                f"Successful {method} request to {operation} at Bangladesh Parliament",
                extra={
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
            
            return validated_response
            
        except requests.exceptions.Timeout as e:
            raise PRPConnectionError(
                f"Timeout connecting to Bangladesh Parliament PRP API for {operation}",
                url=url,
                timeout_seconds=self.config.timeout,
                details={
                    'error': str(e),
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
        except requests.exceptions.ConnectionError as e:
            raise PRPConnectionError(
                f"Connection error for {operation} to Bangladesh Parliament PRP",
                url=url,
                details={
                    'error': str(e),
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
        except requests.exceptions.RequestException as e:
            raise wrap_external_exception(
                e, 
                operation, 
                {
                    'url': url,
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
    
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
            logger.info("Acquiring new PRP authentication token for Bangladesh Parliament")
            self._acquire_token()
        # Check if token needs refresh
        elif self._token_info.needs_refresh:
            logger.info("Refreshing PRP authentication token for Bangladesh Parliament")
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
                f"Requesting new token for Bangladesh Parliament user: {self.config.username}",
                extra={
                    'endpoint': self.config.token_endpoint,
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
            
            response_data = self._make_request(
                method="POST",
                endpoint=self.config.token_endpoint,
                data={
                    "username": self.config.username,
                    "password": self.config.password
                },
                authenticated=False,
                operation="token acquisition for Bangladesh Parliament"
            )
            
            # Extract token from response
            token = response_data[self.config.payload_key]
            if not token or not isinstance(token, str):
                raise PRPAuthenticationError(
                    "Invalid token format in authentication response from Bangladesh Parliament PRP",
                    auth_step="token_extraction",
                    details={
                        'token_type': type(token).__name__,
                        'location': 'Bangladesh Parliament Secretariat'
                    }
                )
            
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Create token info with Bangladesh timezone
            current_time = timezone.now()
            if timezone.is_naive(current_time):
                current_time = BD_TIMEZONE.localize(current_time)
            
            self._token_info = PRPTokenInfo(
                token=token,
                issued_at=current_time
            )
            
            logger.info(
                "Successfully acquired PRP authentication token for Bangladesh Parliament",
                extra={
                    'expires_at': self._token_info.expires_at.isoformat(),
                    'token_length': len(token),
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
            
        except PRPBaseException:
            raise
        except Exception as e:
            raise PRPAuthenticationError(
                f"Token acquisition failed for Bangladesh Parliament: {str(e)}",
                auth_step="token_request",
                username=self.config.username,
                details={
                    'error': str(e),
                    'location': 'Bangladesh Parliament Secretariat'
                }
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
            logger.warning("Maximum token refresh attempts exceeded, acquiring new token for Bangladesh Parliament")
            self._acquire_token()
            return
        
        try:
            logger.info("Refreshing PRP authentication token for Bangladesh Parliament")
            
            response_data = self._make_request(
                method="GET",
                endpoint=self.config.refresh_endpoint,
                authenticated=True,
                operation="token refresh for Bangladesh Parliament"
            )
            
            # Extract refreshed token
            token = response_data[self.config.payload_key]
            if not token or not isinstance(token, str):
                raise PRPAuthenticationError(
                    "Invalid token format in refresh response from Bangladesh Parliament PRP",
                    auth_step="token_refresh",
                    details={
                        'token_type': type(token).__name__,
                        'location': 'Bangladesh Parliament Secretariat'
                    }
                )
            
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Update token info with Bangladesh timezone
            current_time = timezone.now()
            if timezone.is_naive(current_time):
                current_time = BD_TIMEZONE.localize(current_time)
            
            self._token_info.token = token
            self._token_info.issued_at = current_time
            self._token_info.expires_at = current_time + timedelta(seconds=1800)
            self._token_info.refresh_attempts += 1
            
            logger.info(
                "Successfully refreshed PRP authentication token for Bangladesh Parliament",
                extra={
                    'expires_at': self._token_info.expires_at.isoformat(),
                    'refresh_attempt': self._token_info.refresh_attempts,
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
            
        except PRPAuthenticationError:
            logger.warning("Token refresh failed, acquiring new token for Bangladesh Parliament")
            self._acquire_token()
        except Exception as e:
            raise PRPAuthenticationError(
                f"Token refresh failed for Bangladesh Parliament: {str(e)}",
                auth_step="token_refresh",
                details={
                    'error': str(e),
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """
        Retrieve all departments from PRP API at Bangladesh Parliament.
        
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
            PRPBaseException: On API communication errors
        """
        logger.info("Fetching departments from Bangladesh Parliament PRP API")
        
        response_data = self._make_request(
            method="GET",
            endpoint=self.config.departments_endpoint,
            operation="get departments from Bangladesh Parliament PRP"
        )
        
        departments = response_data[self.config.payload_key]
        
        # Validate departments structure
        if not isinstance(departments, list):
            raise PRPDataValidationError(
                "Departments payload must be a list from Bangladesh Parliament PRP",
                expected_type="list",
                actual_value=type(departments).__name__,
                details={'location': 'Bangladesh Parliament Secretariat'}
            )
        
        logger.info(
            f"Successfully retrieved {len(departments)} departments from Bangladesh Parliament PRP",
            extra={
                'department_count': len(departments),
                'location': 'Bangladesh Parliament Secretariat'
            }
        )
        
        return departments
    
    def get_employee_details(self, department_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve employee details for a specific department from Bangladesh Parliament PRP.
        
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
            PRPBaseException: On API communication errors
        """
        if not isinstance(department_id, int) or department_id <= 0:
            raise PRPDataValidationError(
                f"Department ID must be a positive integer for Bangladesh Parliament, got: {department_id}",
                field_name="department_id",
                expected_type="positive integer",
                actual_value=department_id,
                details={'location': 'Bangladesh Parliament Secretariat'}
            )
        
        logger.info(
            f"Fetching employee details for Bangladesh Parliament department ID: {department_id}",
            extra={
                'department_id': department_id,
                'location': 'Bangladesh Parliament Secretariat'
            }
        )
        
        endpoint = self.config.employee_details_endpoint.format(departmentId=department_id)
        
        response_data = self._make_request(
            method="GET",
            endpoint=endpoint,
            operation=f"get employee details for Bangladesh Parliament department {department_id}"
        )
        
        employees = response_data[self.config.payload_key]
        
        # Validate employees structure
        if not isinstance(employees, list):
            raise PRPDataValidationError(
                "Employee details payload must be a list from Bangladesh Parliament PRP",
                expected_type="list",
                actual_value=type(employees).__name__,
                details={
                    'department_id': department_id,
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
        
        logger.info(
            f"Successfully retrieved {len(employees)} employees for Bangladesh Parliament department {department_id}",
            extra={
                'employee_count': len(employees), 
                'department_id': department_id,
                'location': 'Bangladesh Parliament Secretariat'
            }
        )
        
        return employees
    
    def validate_employee_data(self, employee: Dict[str, Any]) -> bool:
        """
        Validate employee data structure for PIMS integration at Bangladesh Parliament.
        
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
                    f"Missing required field for Bangladesh Parliament employee: {field}",
                    field_name=field,
                    details={
                        'employee_data_keys': list(employee.keys()),
                        'location': 'Bangladesh Parliament Secretariat'
                    }
                )
            
            if not employee[field]:
                raise PRPDataValidationError(
                    f"Required field {field} cannot be empty for Bangladesh Parliament employee",
                    field_name=field,
                    actual_value=employee[field],
                    details={'location': 'Bangladesh Parliament Secretariat'}
                )
        
        # Validate field types
        if not isinstance(employee['userId'], str):
            raise PRPDataValidationError(
                "userId must be a string for Bangladesh Parliament employee",
                field_name="userId",
                expected_type="string",
                actual_value=employee['userId'],
                details={'location': 'Bangladesh Parliament Secretariat'}
            )
        
        if employee.get('email') and '@' not in str(employee['email']):
            logger.warning(
                f"Invalid email format for Bangladesh Parliament user {employee['userId']}: {employee['email']}",
                extra={
                    'user_id': employee['userId'], 
                    'email': employee['email'],
                    'location': 'Bangladesh Parliament Secretariat'
                }
            )
        
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test PRP API connection and authentication for Bangladesh Parliament.
        
        Returns:
            Dictionary with connection test results
        """
        current_time = timezone.now()
        if timezone.is_naive(current_time):
            current_time = BD_TIMEZONE.localize(current_time)
        
        test_result = {
            'success': False,
            'timestamp': current_time.isoformat(),
            'base_url': self.config.base_url,
            'username': self.config.username,
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'timezone': 'Asia/Dhaka',
            'tests': {}
        }
        
        try:
            # Test 1: Token acquisition
            logger.info("Testing PRP API connection for Bangladesh Parliament...")
            self._acquire_token()
            test_result['tests']['authentication'] = {
                'success': True,
                'message': 'Token acquired successfully for Bangladesh Parliament'
            }
            
            # Test 2: Departments endpoint
            try:
                departments = self.get_departments()
                test_result['tests']['departments_endpoint'] = {
                    'success': True,
                    'message': f'Retrieved {len(departments)} departments from Bangladesh Parliament PRP'
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
                        'message': f'Retrieved {len(employees)} employees from Bangladesh Parliament department {dept_id}'
                    }
                else:
                    test_result['tests']['employee_details_endpoint'] = {
                        'success': False,
                        'message': 'No departments available for testing at Bangladesh Parliament'
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
            f"PRP API connection test completed for Bangladesh Parliament: {'SUCCESS' if test_result['success'] else 'FAILURE'}",
            extra={
                **test_result,
                'location': 'Bangladesh Parliament Secretariat'
            }
        )
        
        return test_result
    
    def get_sync_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of PRP sync status for Bangladesh Parliament operations.
        
        Returns:
            Dictionary with sync status information
        """
        current_time = timezone.now()
        if timezone.is_naive(current_time):
            current_time = BD_TIMEZONE.localize(current_time)
        
        status_summary = {
            'timestamp': current_time.isoformat(),
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'timezone': 'Asia/Dhaka',
            'api_base_url': self.config.base_url,
            'client_status': 'connected' if self._token_info and not self._token_info.is_expired else 'disconnected',
            'token_info': None
        }
        
        if self._token_info:
            status_summary['token_info'] = {
                'issued_at': self._token_info.issued_at.isoformat(),
                'expires_at': self._token_info.expires_at.isoformat(),
                'is_expired': self._token_info.is_expired,
                'needs_refresh': self._token_info.needs_refresh,
                'refresh_attempts': self._token_info.refresh_attempts
            }
        
        return status_summary
    
    def close(self):
        """Close the client session and cleanup resources."""
        if self.session:
            self.session.close()
            logger.info(
                "PRP Client session closed for Bangladesh Parliament",
                extra={'location': 'Bangladesh Parliament Secretariat'}
            )


# ============================================================================
# Convenience Functions for Bangladesh Parliament Operations
# ============================================================================

def create_prp_client(
    base_url: Optional[str] = None,
    username: Optional[str] = None, 
    password: Optional[str] = None
) -> PRPClient:
    """
    Create a configured PRP client instance for Bangladesh Parliament Secretariat.
    
    Args:
        base_url: PRP API base URL (defaults to Bangladesh Parliament settings)
        username: PRP username (defaults to official credentials)
        password: PRP password (defaults to official credentials)
        
    Returns:
        Configured PRPClient instance for Bangladesh Parliament operations
        
    Example:
        client = create_prp_client()
        departments = client.get_departments()
    """
    return PRPClient(
        base_url=base_url or 'https://prp.parliament.gov.bd',
        username=username or 'ezzetech',
        password=password or '${Fty#3a'
    )


def test_prp_connection(
    base_url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test PRP API connection for Bangladesh Parliament without creating persistent client.
    
    Args:
        base_url: PRP API base URL to test
        username: Username for authentication
        password: Password for authentication
        
    Returns:
        Dictionary with test results
        
    Example:
        result = test_prp_connection()
        if result['success']:
            print("Bangladesh Parliament PRP connection successful!")
    """
    client = None
    try:
        client = create_prp_client(base_url, username, password)
        return client.test_connection()
    finally:
        if client:
            client.close()


def get_bangladesh_parliament_departments(
    client: Optional[PRPClient] = None
) -> List[Dict[str, Any]]:
    """
    Quick function to get departments from Bangladesh Parliament PRP.
    
    Args:
        client: Optional existing PRPClient instance
        
    Returns:
        List of department dictionaries
        
    Example:
        departments = get_bangladesh_parliament_departments()
        for dept in departments:
            print(f"Department: {dept['nameEng']}")
    """
    if client:
        return client.get_departments()
    
    temp_client = None
    try:
        temp_client = create_prp_client()
        return temp_client.get_departments()
    finally:
        if temp_client:
            temp_client.close()


def get_bangladesh_parliament_employees(
    department_id: int,
    client: Optional[PRPClient] = None
) -> List[Dict[str, Any]]:
    """
    Quick function to get employees from Bangladesh Parliament PRP department.
    
    Args:
        department_id: Department ID to retrieve employees from
        client: Optional existing PRPClient instance
        
    Returns:
        List of employee dictionaries
        
    Example:
        employees = get_bangladesh_parliament_employees(1)
        for emp in employees:
            print(f"Employee: {emp['nameEng']} - {emp['designationEng']}")
    """
    if client:
        return client.get_employee_details(department_id)
    
    temp_client = None
    try:
        temp_client = create_prp_client()
        return temp_client.get_employee_details(department_id)
    finally:
        if temp_client:
            temp_client.close()


# ============================================================================
# Template Design Pattern Utilities
# ============================================================================

def get_prp_client_template_config() -> Dict[str, Any]:
    """
    Get template configuration for PRP client UI elements.
    
    Returns template design configuration following flat design patterns
    with high contrast colors for Bangladesh Parliament Secretariat.
    
    Returns:
        Dictionary with template configuration
    """
    return {
        'design_system': 'flat_design',
        'glassmorphism': False,  # NO glassmorphism as specified
        'colors': {
            'primary': '#28a745',   # Teal
            'secondary': '#fd7e14', # Orange  
            'danger': '#dc3545',    # Red
            'success': '#28a745',   # Teal
            'warning': '#ffc107',   # Yellow
            'info': '#17a2b8'       # Light Blue
        },
        'location': 'Bangladesh Parliament Secretariat, Dhaka',
        'timezone': 'Asia/Dhaka',
        'responsive_breakpoints': {
            'mobile': '576px',
            'tablet': '768px', 
            'laptop': '992px',
            'desktop': '1200px',
            'big_monitors': '1400px'
        },
        'prp_styling': {
            'readonly_field_bg': '#f8f9fa',
            'readonly_field_border': '#28a745',
            'prp_indicator_color': '#28a745',
            'sync_status_colors': {
                'synced': '#28a745',
                'pending': '#fd7e14', 
                'error': '#dc3545'
            }
        }
    }


def format_bangladesh_time(dt: datetime) -> str:
    """
    Format datetime for Bangladesh Parliament operations.
    
    Args:
        dt: Datetime to format
        
    Returns:
        Formatted datetime string in Asia/Dhaka timezone
    """
    if timezone.is_naive(dt):
        dt = BD_TIMEZONE.localize(dt)
    elif dt.tzinfo != BD_TIMEZONE:
        dt = dt.astimezone(BD_TIMEZONE)
    
    return dt.strftime('%Y-%m-%d %H:%M:%S %Z')


def log_bangladesh_parliament_operation(
    operation: str,
    details: Dict[str, Any],
    level: str = 'info'
) -> None:
    """
    Log operation with Bangladesh Parliament context.
    
    Args:
        operation: Description of the operation
        details: Additional operation details
        level: Log level (info, warning, error)
    """
    log_data = {
        'operation': operation,
        'location': 'Bangladesh Parliament Secretariat, Dhaka',
        'timezone': 'Asia/Dhaka',
        'timestamp': format_bangladesh_time(timezone.now()),
        **details
    }
    
    if level == 'warning':
        logger.warning(f"Bangladesh Parliament PRP: {operation}", extra=log_data)
    elif level == 'error':
        logger.error(f"Bangladesh Parliament PRP: {operation}", extra=log_data)
    else:
        logger.info(f"Bangladesh Parliament PRP: {operation}", extra=log_data)


# Export classes and functions for Bangladesh Parliament PIMS integration
__all__ = [
    # Core classes
    'PRPClient',
    'PRPAPIConfig', 
    'PRPTokenInfo',
    
    # Convenience functions
    'create_prp_client',
    'test_prp_connection',
    'get_bangladesh_parliament_departments',
    'get_bangladesh_parliament_employees',
    
    # Template utilities
    'get_prp_client_template_config',
    'format_bangladesh_time',
    'log_bangladesh_parliament_operation',
]