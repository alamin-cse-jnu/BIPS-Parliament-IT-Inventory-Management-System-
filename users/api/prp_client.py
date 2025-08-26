"""
PRP (Parliament Resource Portal) API Client
============================================

Complete API client for PRP integration with PIMS at Bangladesh Parliament Secretariat, Dhaka.

This module provides comprehensive PRP API integration including:
- Authentication with token management
- User lookup and synchronization
- Department management
- Error handling and logging
- Mock mode for development

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Complete PRP API client with production and development support

Usage Example:
--------------
from users.api.prp_client import create_prp_client

# Create client (automatically handles settings)
client = create_prp_client()

# Authenticate
if client.authenticate():
    # Lookup user
    user_data = client.lookup_user_by_employee_id('110100092')
    
    # Get departments
    departments = client.get_departments()
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from .exceptions import (
    PRPException,
    PRPConnectionError,
    PRPAuthenticationError,
    PRPDataValidationError,
    PRPConfigurationError
)

# Configure logging
logger = logging.getLogger('pims.prp_integration.client')


class PRPClient:
    """
    Complete PRP (Parliament Resource Portal) API Client.
    
    Handles authentication, user lookup, department sync, and all PRP operations
    with comprehensive error handling and caching for Bangladesh Parliament Secretariat.
    """
    
    def __init__(
        self, 
        base_url: str = None, 
        username: str = None, 
        password: str = None, 
        timeout: int = 30,
        enable_caching: bool = True
    ):
        """
        Initialize PRP client with configuration.
        
        Args:
            base_url: PRP API base URL
            username: PRP API username
            password: PRP API password  
            timeout: Request timeout in seconds
            enable_caching: Enable response caching
        """
        # Set configuration with fallbacks
        self.base_url = (base_url or 
                        os.environ.get('PRP_API_BASE_URL') or 
                        'https://prp.parliament.gov.bd')
        
        self.username = (username or 
                        os.environ.get('PRP_API_USERNAME') or 
                        'ezzetech')
        
        self.password = (password or 
                        os.environ.get('PRP_API_PASSWORD') or 
                        '${Fty#3a')
        
        self.timeout = timeout
        self.enable_caching = enable_caching
        
        # Clean up base URL
        self.base_url = self.base_url.rstrip('/')
        if self.base_url.endswith('/api'):
            self.base_url = self.base_url[:-4]
        
        # Initialize state
        self.token = None
        self.token_expires = None
        self.session = None
        self.last_auth_time = None
        
        # Setup session
        self._setup_session()
        
        logger.info(f"PRP Client initialized for Bangladesh Parliament Secretariat")
        logger.info(f"Base URL: {self.base_url}, Username: {self.username}")
    
    def _setup_session(self):
        """Setup requests session with proper configuration."""
        self.session = requests.Session()
        
        # Configure session
        self.session.timeout = self.timeout
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'PIMS-PRP-Integration/1.0 (Bangladesh Parliament Secretariat)',
            'X-Client-Location': 'Dhaka, Bangladesh',
            'X-Client-System': 'PIMS'
        })
        
        # Configure retries
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _is_token_valid(self) -> bool:
        """Check if current token is valid and not expired."""
        if not self.token:
            return False
            
        if not self.token_expires:
            # If no expiry info, consider valid for 1 hour from last auth
            if self.last_auth_time:
                return (timezone.now() - self.last_auth_time).total_seconds() < 3600
            return False
            
        return timezone.now() < self.token_expires
    
    def authenticate(self) -> bool:
        """
        Authenticate with PRP API and obtain access token.
        
        Returns:
            bool: True if authentication successful, False otherwise
            
        Raises:
            PRPAuthenticationError: If authentication fails
            PRPConnectionError: If network connection fails
        """
        # Check if current token is still valid
        if self._is_token_valid():
            logger.debug("Using existing valid token")
            return True
        
        auth_url = f"{self.base_url}/api/authentication/external"
        
        auth_payload = {
            "action": "token",
            "username": self.username,
            "password": self.password
        }
        
        try:
            logger.info(f"Authenticating with PRP API: {auth_url}")
            
            response = self.session.post(
                auth_url,
                json=auth_payload,
                timeout=self.timeout
            )
            
            logger.debug(f"Auth response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if data.get('responseCode') == 200 and 'payload' in data:
                        token_data = data['payload']
                        
                        if isinstance(token_data, dict) and 'token' in token_data:
                            self.token = token_data['token']
                            
                            # Set token expiry (default to 24 hours)
                            expires_in = token_data.get('expiresIn', 86400)  # 24 hours default
                            self.token_expires = timezone.now() + timedelta(seconds=expires_in)
                            
                            # Update session headers
                            self.session.headers['Authorization'] = f'Bearer {self.token}'
                            self.last_auth_time = timezone.now()
                            
                            logger.info("PRP authentication successful")
                            return True
                        else:
                            error_msg = "Invalid token format in response"
                            logger.error(f"Auth error: {error_msg}")
                            raise PRPAuthenticationError(error_msg, details=token_data)
                    else:
                        error_msg = data.get('msg', 'Authentication failed')
                        logger.error(f"Auth failed: {error_msg}")
                        raise PRPAuthenticationError(error_msg, details=data)
                        
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON response: {e}"
                    logger.error(f"Auth JSON error: {error_msg}")
                    logger.error(f"Response content: {response.text[:500]}")
                    raise PRPAuthenticationError(error_msg)
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"Auth HTTP error: {error_msg}")
                raise PRPConnectionError(f"Authentication failed: {error_msg}")
                
        except requests.exceptions.Timeout:
            error_msg = f"Authentication timeout after {self.timeout}s"
            logger.error(error_msg)
            raise PRPConnectionError(error_msg)
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            raise PRPConnectionError(error_msg)
            
        except (PRPAuthenticationError, PRPConnectionError):
            # Re-raise PRP exceptions as-is
            raise
            
        except Exception as e:
            error_msg = f"Unexpected authentication error: {str(e)}"
            logger.error(error_msg)
            raise PRPAuthenticationError(error_msg)
    
    def _make_authenticated_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any] = None,
        method: str = 'GET',
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to PRP API.
        
        Args:
            endpoint: API endpoint path
            params: URL parameters
            method: HTTP method
            data: Request body data
            
        Returns:
            dict: API response data
            
        Raises:
            PRPConnectionError: If request fails
            PRPAuthenticationError: If authentication fails
        """
        # Ensure we're authenticated
        if not self.authenticate():
            raise PRPAuthenticationError("Failed to authenticate with PRP API")
        
        url = f"{self.base_url}/api/secure/external"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, params=params, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.debug(f"API request: {method} {url} - Status: {response.status_code}")
            
            if response.status_code == 401:
                # Token might be expired, clear it and retry once
                logger.warning("Got 401, clearing token and retrying")
                self.token = None
                self.token_expires = None
                self.session.headers.pop('Authorization', None)
                
                # Retry authentication
                if self.authenticate():
                    # Retry the original request
                    if method.upper() == 'GET':
                        response = self.session.get(url, params=params, timeout=self.timeout)
                    else:
                        response = self.session.post(url, params=params, json=data, timeout=self.timeout)
                else:
                    raise PRPAuthenticationError("Re-authentication failed")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if data.get('responseCode') == 200:
                        return data.get('payload', {})
                    else:
                        error_msg = data.get('msg', f'API error: {data.get("responseCode")}')
                        logger.error(f"API error response: {error_msg}")
                        raise PRPException(error_msg, details=data)
                        
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON response: {e}"
                    logger.error(error_msg)
                    logger.error(f"Response content: {response.text[:500]}")
                    raise PRPException(error_msg)
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"API HTTP error: {error_msg}")
                raise PRPConnectionError(error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout}s"
            logger.error(error_msg)
            raise PRPConnectionError(error_msg)
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            raise PRPConnectionError(error_msg)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to PRP API.
        
        Returns:
            dict: Connection test results
        """
        try:
            # Try to get departments as a connection test
            departments = self.get_departments()
            
            return {
                'success': True,
                'message': f'Connection successful - {len(departments)} departments found',
                'timestamp': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            }
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """
        Get all departments from PRP API.
        
        Returns:
            list: List of department objects
            
        Raises:
            PRPConnectionError: If API request fails
        """
        cache_key = 'prp_departments'
        
        # Check cache first
        if self.enable_caching:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug("Returning cached departments")
                return cached_data
        
        try:
            params = {'action': 'departments'}
            data = self._make_authenticated_request('departments', params=params)
            
            # Handle both array and object responses
            if isinstance(data, list):
                departments = data
            elif isinstance(data, dict) and 'departments' in data:
                departments = data['departments']
            else:
                departments = []
            
            # Validate and clean department data
            validated_departments = []
            for dept in departments:
                if isinstance(dept, dict) and 'id' in dept:
                    validated_departments.append({
                        'id': dept.get('id'),
                        'nameEng': dept.get('nameEng', f"Department {dept.get('id')}"),
                        'nameBng': dept.get('nameBng', ''),
                        'isWing': bool(dept.get('isWing', False))
                    })
            
            # Cache the results
            if self.enable_caching:
                cache.set(cache_key, validated_departments, 3600)  # Cache for 1 hour
                cache.set(f'{cache_key}_last_sync', timezone.now(), 3600)
            
            logger.info(f"Retrieved {len(validated_departments)} departments from PRP")
            return validated_departments
            
        except Exception as e:
            logger.error(f"Failed to get departments: {e}")
            raise
    
    def get_department_employees(self, department_id: int) -> List[Dict[str, Any]]:
        """
        Get all employees from a specific department.
        
        Args:
            department_id: Department ID
            
        Returns:
            list: List of employee objects
            
        Raises:
            PRPConnectionError: If API request fails
        """
        try:
            params = {
                'action': 'employee_details',
                'departmentId': department_id
            }
            
            data = self._make_authenticated_request('employees', params=params)
            
            # Handle response format
            if isinstance(data, list):
                employees = data
            elif isinstance(data, dict) and 'employees' in data:
                employees = data['employees']
            else:
                employees = []
            
            # Validate employee data
            validated_employees = []
            for emp in employees:
                if isinstance(emp, dict) and 'userId' in emp:
                    validated_employees.append({
                        'userId': emp.get('userId'),
                        'nameEng': emp.get('nameEng', ''),
                        'email': emp.get('email', ''),
                        'designationEng': emp.get('designationEng', ''),
                        'mobile': emp.get('mobile', ''),
                        'status': emp.get('status', 'unknown'),
                        'departmentId': department_id,
                        'photo': emp.get('photo')  # Base64 encoded photo
                    })
            
            logger.info(f"Retrieved {len(validated_employees)} employees from department {department_id}")
            return validated_employees
            
        except Exception as e:
            logger.error(f"Failed to get employees for department {department_id}: {e}")
            raise
    
    def lookup_user_by_employee_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Lookup a specific user by employee ID.
        
        Args:
            employee_id: Employee ID to lookup
            
        Returns:
            dict or None: User data if found, None if not found
            
        Raises:
            PRPConnectionError: If API request fails
        """
        try:
            # Get all departments first
            departments = self.get_departments()
            
            # Search through each department
            for dept in departments:
                try:
                    employees = self.get_department_employees(dept['id'])
                    
                    # Look for the employee in this department
                    for emp in employees:
                        if str(emp.get('userId')) == str(employee_id):
                            logger.info(f"Found employee {employee_id} in department {dept['nameEng']}")
                            return emp
                            
                except Exception as e:
                    logger.warning(f"Error searching department {dept['id']}: {e}")
                    continue
            
            logger.info(f"Employee {employee_id} not found in any department")
            return None
            
        except Exception as e:
            logger.error(f"Failed to lookup user {employee_id}: {e}")
            raise
    
    def refresh_token(self) -> bool:
        """
        Refresh the authentication token.
        
        Returns:
            bool: True if refresh successful
        """
        try:
            # Clear existing token
            self.token = None
            self.token_expires = None
            self.session.headers.pop('Authorization', None)
            
            # Re-authenticate
            return self.authenticate()
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False
    
    def clear_cache(self):
        """Clear all cached PRP data."""
        if self.enable_caching:
            cache_keys = ['prp_departments', 'prp_departments_last_sync']
            for key in cache_keys:
                cache.delete(key)
            logger.info("PRP cache cleared")


class MockPRPClient:
    """
    Mock PRP client for development and testing.
    
    Provides the same interface as PRPClient but returns mock data
    when the real PRP API is not accessible during development.
    """
    
    def __init__(self):
        """Initialize mock client."""
        self.base_url = 'https://prp.parliament.gov.bd'
        self.username = 'ezzetech'
        self.token = 'mock_token_bangladesh_parliament'
        self.authenticated = True
        
        logger.info("🎭 Mock PRP Client initialized for Bangladesh Parliament Secretariat")
        logger.warning("⚠️  Using MOCK data - not connected to real PRP API")
    
    def authenticate(self) -> bool:
        """Mock authentication - always succeeds."""
        logger.info("✅ Mock authentication successful")
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """Mock connection test."""
        return {
            'success': True,
            'message': 'Mock connection test successful',
            'timestamp': timezone.now().isoformat(),
            'location': 'Bangladesh Parliament Secretariat, Dhaka (MOCK MODE)'
        }
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """Return mock departments data."""
        mock_departments = [
            {'id': 1, 'nameEng': 'Administration', 'nameBng': 'প্রশাসন', 'isWing': False},
            {'id': 2, 'nameEng': 'IT Department', 'nameBng': 'আইটি বিভাগ', 'isWing': False},
            {'id': 3, 'nameEng': 'Finance', 'nameBng': 'অর্থ', 'isWing': False},
            {'id': 4, 'nameEng': 'Human Resources', 'nameBng': 'মানবসম্পদ', 'isWing': False},
            {'id': 5, 'nameEng': 'Security', 'nameBng': 'নিরাপত্তা', 'isWing': False},
            {'id': 6, 'nameEng': 'Library', 'nameBng': 'গ্রন্থাগার', 'isWing': False},
            {'id': 7, 'nameEng': 'Transport', 'nameBng': 'পরিবহন', 'isWing': False},
        ]
        
        logger.info(f"🎭 Returning {len(mock_departments)} mock departments")
        return mock_departments
    
    def get_department_employees(self, department_id: int) -> List[Dict[str, Any]]:
        """Return mock employee data for department."""
        mock_employees = [
            {
                'userId': f'11010009{department_id}',
                'nameEng': f'Ahmed Rahman Khan (Dept {department_id})',
                'email': f'ahmed.rahman{department_id}@parliament.gov.bd',
                'designationEng': 'Senior Officer',
                'mobile': f'+880 1712-{department_id}45678',
                'status': 'active',
                'departmentId': department_id,
                'photo': None
            },
            {
                'userId': f'11010010{department_id}',
                'nameEng': f'Fatima Begum (Dept {department_id})',
                'email': f'fatima.begum{department_id}@parliament.gov.bd',
                'designationEng': 'Assistant Officer',
                'mobile': f'+880 1812-{department_id}56789',
                'status': 'active',
                'departmentId': department_id,
                'photo': None
            }
        ]
        
        logger.info(f"🎭 Returning {len(mock_employees)} mock employees for department {department_id}")
        return mock_employees
    
    def lookup_user_by_employee_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Mock user lookup."""
        # Generate mock data based on employee ID
        if employee_id and employee_id.isdigit():
            dept_id = int(employee_id[-1:]) or 2  # Use last digit as dept ID
            
            mock_user = {
                'userId': employee_id,
                'nameEng': f'Mock Employee {employee_id}',
                'email': f'employee.{employee_id}@parliament.gov.bd',
                'designationEng': 'Senior System Administrator',
                'mobile': f'+880 1712-{employee_id[-6:]}',
                'status': 'active',
                'departmentId': dept_id,
                'photo': None
            }
            
            logger.info(f"🎭 Mock lookup successful for employee {employee_id}")
            return mock_user
        
        logger.info(f"🎭 Mock lookup - employee {employee_id} not found")
        return None
    
    def refresh_token(self) -> bool:
        """Mock token refresh."""
        return True
    
    def clear_cache(self):
        """Mock cache clear."""
        logger.info("🎭 Mock cache cleared")


def create_prp_client() -> Union[PRPClient, MockPRPClient]:
    """
    Factory function to create appropriate PRP client.
    
    Creates either a real PRP client or mock client based on configuration.
    Automatically handles Django settings integration.
    
    Returns:
        PRPClient or MockPRPClient: Configured PRP client instance
        
    Raises:
        PRPConfigurationError: If configuration is invalid
    """
    try:
        # Check if we're in mock mode (development only)
        mock_mode = (
            os.environ.get('PRP_MOCK_MODE', 'false').lower() == 'true' and
            getattr(settings, 'DEBUG', False)
        )
        
        if mock_mode:
            logger.info("🎭 Creating Mock PRP client for development")
            return MockPRPClient()
        
        # Get configuration from multiple sources
        prp_settings = getattr(settings, 'PRP_API_SETTINGS', {})
        
        # Determine configuration
        base_url = (
            os.environ.get('PRP_API_BASE_URL') or 
            prp_settings.get('BASE_URL') or 
            'https://prp.parliament.gov.bd'
        )
        
        username = (
            os.environ.get('PRP_API_USERNAME') or 
            prp_settings.get('USERNAME') or 
            'ezzetech'
        )
        
        password = (
            os.environ.get('PRP_API_PASSWORD') or 
            prp_settings.get('PASSWORD') or 
            '${Fty#3a'
        )
        
        timeout = int(
            os.environ.get('PRP_API_TIMEOUT') or 
            prp_settings.get('TIMEOUT') or 
            30
        )
        
        # Validate configuration
        if not all([base_url, username, password]):
            raise PRPConfigurationError(
                "Missing required PRP configuration",
                details={
                    'base_url': bool(base_url),
                    'username': bool(username), 
                    'password': bool(password),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
        
        logger.info("🔧 Creating PRP client for Bangladesh Parliament Secretariat")
        logger.info(f"🔗 Base URL: {base_url}")
        logger.info(f"👤 Username: {username}")
        logger.info(f"⏱️ Timeout: {timeout}s")
        
        client = PRPClient(
            base_url=base_url,
            username=username,
            password=password,
            timeout=timeout
        )
        
        return client
        
    except Exception as e:
        logger.error(f"Failed to create PRP client: {e}")
        raise PRPConfigurationError(
            f"PRP client creation failed: {str(e)}",
            details={
                'location': 'Bangladesh Parliament Secretariat, Dhaka',
                'error': str(e)
            }
        )