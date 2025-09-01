"""
REAL PRP (Parliament Resource Portal) API Client - NO MOCK DATA
===============================================================

Complete API client for real PRP integration with PIMS at Bangladesh Parliament Secretariat.
This replaces ALL mock functionality with actual PRP API calls.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Real PRP API client with production authentication and data retrieval

API Details (From Official PRP Documentation):
- Base URL: https://prp.parliament.gov.bd
- Authentication: Bearer token (username: "ezzetech", password: "${Fty#3a")
- Response Format: {responseCode: 200, payload: [...], msg: "Success"}

Key Endpoints:
1. Authentication: POST /api/authentication/external?action=token
2. Employee Details: GET /api/secure/external?action=employee_details&departmentId={id}
3. Departments: GET /api/secure/external?action=departments
4. Token Refresh: GET /api/authentication/external?action=refresh-token

Data Models (PIMS Integration Scope):
- EmployeeDetails: {userId, nameEng, designationEng, email, mobile, photo, status}
- DepartmentModel: {id, nameEng, nameBng, isWing}

Usage Example:
--------------
from users.api.prp_client import PRPClient

# Create real PRP client
client = PRPClient()

# Authenticate with PRP
if client.authenticate():
    # Get departments
    departments = client.get_departments()
    
    # Get employees from specific department
    employees = client.get_department_employees(department_id=1)
    
    # Lookup specific user
    user = client.lookup_user_by_employee_id('110100091')
"""

import base64
import io
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.core.files.base import ContentFile

# Import PRP exceptions from the exceptions module
from .exceptions import (
    PRPException,
    PRPConnectionError,
    PRPAuthenticationError,
    PRPDataValidationError,
    PRPConfigurationError,
    PRPBusinessRuleError,
    wrap_external_exception
)

# Configure logging
logger = logging.getLogger('pims.prp_integration.client')


class PRPClient:
    """
    Real PRP (Parliament Resource Portal) API Client.
    
    Handles all communication with the live PRP API at Bangladesh Parliament Secretariat.
    NO MOCK DATA - all operations use real API endpoints.
    """
    
    def __init__(
        self, 
        base_url: str = None, 
        username: str = None, 
        password: str = None, 
        timeout: int = 30,
        enable_caching: bool = True
    ):

        # Get PRP settings from Django settings
        prp_settings = getattr(settings, 'PRP_API_SETTINGS', {})
    
        # Production PRP API Configuration (Bangladesh Parliament Secretariat)
        self.base_url = base_url or prp_settings.get('BASE_URL', 'https://prp.parliament.gov.bd')
        self.username = username or prp_settings.get('AUTH_USERNAME', 'ezzetech')
        self.password = password or prp_settings.get('AUTH_PASSWORD', '${Fty#3a')
        self.timeout = timeout or prp_settings.get('TIMEOUT', 30)
        self.enable_caching = enable_caching
    
        #  SSL Configuration from settings
        self.verify_ssl = prp_settings.get('VERIFY_SSL', True)
    
        # Authentication state
        self.token = None
        self.token_expires = None
        self.last_auth_time = None
    
        #  HTTP session with SSL configuration
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PIMS-PRP-Integration/1.0 (Bangladesh Parliament Secretariat)',
            'Accept': 'application/json'
        })
    
        #  Apply SSL verification setting
        if not self.verify_ssl:
            self.session.verify = False
            # Disable SSL warnings
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("⚠️  SSL verification disabled for PRP API")
    
        #  Add retry strategy for reliability
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
    
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
        logger.info(f"  PRP Client initialized for Bangladesh Parliament Secretariat")
        logger.info(f" API Base URL: {self.base_url}")
        logger.info(f" Username: {self.username}")
        logger.info(f" SSL Verification: {'Enabled' if self.verify_ssl else 'Disabled'}")
        logger.info(f"Location: Dhaka, Bangladesh")
    
    def authenticate(self) -> bool:
        """
        Authenticate with PRP API using real credentials.
        
        Returns:
            bool: True if authentication successful, False otherwise
            
        Raises:
            PRPConnectionError: If network/HTTP error occurs
            PRPAuthenticationError: If authentication fails
        """
        # Check if we already have a valid token
        if self.token and self.token_expires and timezone.now() < self.token_expires:
            logger.debug("Using existing valid token")
            return True
        
        logger.info(" Authenticating with PRP API...")
        
        try:
            # Prepare authentication request (Real PRP API format)
            auth_url = f"{self.base_url}/api/authentication/external"
            auth_payload = {
                "username": self.username,
                "password": self.password
            }
            auth_params = {"action": "token"}
            
            # Make authentication request
            response = self.session.post(
                auth_url,
                params=auth_params,
                json=auth_payload,
                timeout=self.timeout
            )
            
            logger.info(f" Auth request to: {auth_url}")
            logger.info(f" Response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.debug(f"📋 Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    # Check PRP API response format
                    if data.get('responseCode') == 200:
                        # Extract token from payload
                        token_payload = data.get('payload', '')
                        
                        if token_payload and isinstance(token_payload, str):
                            # Handle different token formats
                            if token_payload.startswith('Bearer '):
                                self.token = token_payload[7:]  # Remove 'Bearer ' prefix
                            else:
                                self.token = token_payload
                            
                            # Set token expiry (estimate 24 hours for PRP tokens)
                            self.token_expires = timezone.now() + timedelta(hours=24)
                            self.last_auth_time = timezone.now()
                            
                            # Update session headers
                            self.session.headers['Authorization'] = f'Bearer {self.token}'
                            
                            logger.info(" PRP authentication successful")
                            logger.info(f" Token received (length: {len(self.token)} chars)")
                            return True
                        else:
                            error_msg = "No token in PRP response payload"
                            logger.error(f" {error_msg}")
                            raise PRPAuthenticationError(error_msg)
                    else:
                        error_msg = data.get('msg', 'Authentication failed')
                        logger.error(f" PRP auth failed: {error_msg}")
                        raise PRPAuthenticationError(f"PRP API Error: {error_msg}")
                        
                except json.JSONDecodeError as e:
                    raise wrap_external_exception(e, "authentication JSON parsing", {
                        'response_text': response.text[:200],
                        'url': auth_url
                    })
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f" Auth HTTP error: {error_msg}")
                raise PRPConnectionError(f"Authentication failed: {error_msg}")
                
        except requests.exceptions.Timeout:
            raise wrap_external_exception(
                requests.exceptions.Timeout(f"Authentication timeout after {self.timeout}s"),
                "PRP authentication",
                {'timeout': self.timeout, 'url': f"{self.base_url}/api/authentication/external"}
            )
            
        except requests.exceptions.ConnectionError as e:
            raise wrap_external_exception(e, "PRP authentication connection", {'url': self.base_url})
            
        except (PRPAuthenticationError, PRPConnectionError):
            # Re-raise PRP exceptions as-is
            raise
            
        except Exception as e:
            error_msg = f"Unexpected authentication error: {str(e)}"
            logger.error(f" {error_msg}")
            raise PRPAuthenticationError(error_msg)
    
    def refresh_token(self) -> bool:
        """
        Refresh the authentication token.
        
        Returns:
            bool: True if token refresh successful
            
        Raises:
            PRPConnectionError: If refresh fails
        """
        logger.info("🔄 Refreshing PRP token...")
        
        try:
            refresh_url = f"{self.base_url}/api/authentication/external"
            refresh_params = {"action": "refresh-token"}
            
            response = self.session.get(
                refresh_url,
                params=refresh_params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('responseCode') == 200:
                    token_payload = data.get('payload', '')
                    
                    if token_payload:
                        if token_payload.startswith('Bearer '):
                            self.token = token_payload[7:]
                        else:
                            self.token = token_payload
                        
                        self.token_expires = timezone.now() + timedelta(hours=24)
                        self.session.headers['Authorization'] = f'Bearer {self.token}'
                        
                        logger.info("Token refresh successful")
                        return True
                    else:
                        logger.error(" No token in refresh response")
                        return False
                else:
                    logger.error(f" Token refresh failed: {data.get('msg', 'Unknown error')}")
                    return False
            else:
                logger.error(f" HTTP {response.status_code} during token refresh")
                return False
                
        except Exception as e:
            logger.error(f" Token refresh error: {e}")
            return False
    
    def _make_authenticated_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any] = None,
        method: str = 'GET'
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to PRP API.
        
        Args:
            endpoint: API endpoint identifier
            params: URL parameters
            method: HTTP method
            
        Returns:
            dict: API response payload data
            
        Raises:
            PRPConnectionError: If request fails
            PRPAuthenticationError: If authentication fails
        """
        # Ensure we're authenticated
        if not self.authenticate():
            raise PRPAuthenticationError("Failed to authenticate with PRP API")
        
        # Build URL for secure endpoints
        url = f"{self.base_url}/api/secure/external"
        
        try:
            logger.debug(f" Making {method} request to PRP: {url}")
            logger.debug(f" Parameters: {params}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, params=params, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.debug(f" Response status: {response.status_code}")
            
            # Handle token expiry
            if response.status_code == 401:
                logger.warning("🔓 Got 401, token might be expired. Trying to refresh...")
                
                # Clear current token and try refresh
                self.token = None
                self.token_expires = None
                self.session.headers.pop('Authorization', None)
                
                # Try to refresh token
                if self.refresh_token() or self.authenticate():
                    # Retry the original request
                    logger.info(" Retrying request with new token...")
                    if method.upper() == 'GET':
                        response = self.session.get(url, params=params, timeout=self.timeout)
                    else:
                        response = self.session.post(url, params=params, timeout=self.timeout)
                else:
                    raise PRPAuthenticationError("Failed to refresh or re-authenticate")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Validate PRP response format
                    if data.get('responseCode') == 200:
                        payload = data.get('payload', {})
                        logger.debug(f" Successful API response: {data.get('msg', 'Success')}")
                        return payload
                    else:
                        error_msg = data.get('msg', f'API error: {data.get("responseCode")}')
                        logger.error(f" PRP API error: {error_msg}")
                        raise PRPConnectionError(f"PRP API Error: {error_msg}")
                        
                except json.JSONDecodeError as e:
                    raise wrap_external_exception(e, "PRP API response parsing", {
                        'url': url,
                        'response_text': response.text[:500],
                        'status_code': response.status_code
                    })
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f" Request failed: {error_msg}")
                raise PRPConnectionError(error_msg)
                
        except requests.exceptions.Timeout:
            raise wrap_external_exception(
                requests.exceptions.Timeout(f"Request timeout after {self.timeout}s"),
                "PRP API request",
                {'url': url, 'params': params, 'timeout': self.timeout}
            )
            
        except requests.exceptions.ConnectionError as e:
            raise wrap_external_exception(e, "PRP API connection", {'url': url, 'params': params})
            
        except (PRPAuthenticationError, PRPConnectionError):
            # Re-raise PRP exceptions as-is
            raise
            
        except Exception as e:
            error_msg = f"Unexpected request error: {str(e)}"
            logger.error(f" {error_msg}")
            raise PRPConnectionError(error_msg)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to PRP API.
        
        Returns:
            dict: Connection test results
        """
        logger.info("🔍 Testing PRP API connection...")
        
        try:
            # Test authentication
            auth_success = self.authenticate()
            
            if auth_success:
                # Test a simple API call (departments)
                try:
                    departments = self.get_departments()
                    
                    return {
                        'success': True,
                        'message': 'PRP connection successful',
                        'timestamp': timezone.now().isoformat(),
                        'location': 'Bangladesh Parliament Secretariat, Dhaka',
                        'api_url': self.base_url,
                        'departments_count': len(departments),
                        'token_valid': bool(self.token),
                        'details': {
                            'authentication': 'SUCCESS',
                            'api_access': 'SUCCESS',
                            'data_retrieval': 'SUCCESS'
                        }
                    }
                    
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'API access failed: {str(e)}',
                        'timestamp': timezone.now().isoformat(),
                        'location': 'Bangladesh Parliament Secretariat, Dhaka',
                        'api_url': self.base_url,
                        'token_valid': bool(self.token),
                        'details': {
                            'authentication': 'SUCCESS',
                            'api_access': 'FAILED',
                            'error': str(e)
                        }
                    }
            else:
                return {
                    'success': False,
                    'message': 'PRP authentication failed',
                    'timestamp': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka',
                    'api_url': self.base_url,
                    'token_valid': False,
                    'details': {
                        'authentication': 'FAILED',
                        'api_access': 'NOT_TESTED'
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'timestamp': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka',
                'api_url': self.base_url,
                'token_valid': False,
                'details': {
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            }
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """
        Get list of departments from PRP API.
        
        API Endpoint: GET /api/secure/external?action=departments
        Response Model: DepartmentModel{id, nameEng, nameBng, isWing}
        
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
                logger.debug(f"📦 Returning {len(cached_data)} cached departments")
                return cached_data
        
        try:
            logger.info("Fetching departments from PRP API...")
            
            params = {'action': 'departments'}
            data = self._make_authenticated_request('departments', params=params)
            
            # Handle response format - PRP returns array directly in payload
            if isinstance(data, list):
                departments = data
            else:
                # Fallback for different response structures
                departments = []
                logger.warning(f"  Unexpected departments response format: {type(data)}")
            
            # Validate and clean department data according to PRP DepartmentModel
            validated_departments = []
            for dept in departments:
                if isinstance(dept, dict) and 'id' in dept:
                    validated_departments.append({
                        'id': int(dept.get('id')),
                        'nameEng': dept.get('nameEng', f"Department {dept.get('id')}"),
                        'nameBng': dept.get('nameBng', ''),
                        'isWing': bool(dept.get('isWing', False))
                    })
                else:
                    logger.warning(f"  Invalid department data: {dept}")
            
            # Cache the validated results
            if self.enable_caching and validated_departments:
                cache.set(cache_key, validated_departments, 3600)  # Cache for 1 hour
                cache.set(f'{cache_key}_last_sync', timezone.now(), 3600)
                logger.debug(f"Cached {len(validated_departments)} departments")
            
            logger.info(f" Retrieved {len(validated_departments)} departments from PRP")
            return validated_departments
            
        except Exception as e:
            logger.error(f" Failed to get departments: {e}")
            raise PRPConnectionError(f"Department retrieval failed: {str(e)}")
    
    def get_department_employees(self, department_id: int) -> List[Dict[str, Any]]:
        """Enhanced debug version to see what's happening with employee retrieval."""
        try:
            logger.info(f"🔍 Getting employees for department ID: {department_id}")
            
            params = {
                'action': 'employee_details',
                'departmentId': department_id
            }
            
            response_data = self._make_authenticated_request('employee_details', params)
            
            # Enhanced debug logging
            logger.info(f" Response type: {type(response_data)}")
            if isinstance(response_data, dict):
                logger.info(f" Response keys: {list(response_data.keys())}")
                logger.info(f" Response code: {response_data.get('responseCode', 'N/A')}")
                logger.info(f"Response message: {response_data.get('msg', 'N/A')}")
            
            employees = response_data.get('payload', [])
            
            logger.info(f"👥 Raw employee payload type: {type(employees)}")
            if isinstance(employees, list):
                logger.info(f"👥 Raw employee count: {len(employees)}")
            else:
                logger.warning(f"  Expected list, got: {employees}")
                return []
            
            if not employees:
                logger.warning(f"  No employees returned for department {department_id}")
                return []
            
            # Enhanced employee processing with debug info
            validated_employees = []
            for i, emp in enumerate(employees):
                if isinstance(emp, dict):
                    user_id = emp.get('userId')
                    name = emp.get('nameEng', 'Unknown')
                    
                    logger.debug(f"👤 Processing employee {i+1}: {name} (ID: {user_id}, type: {type(user_id)})")
                    
                    validated_employee = {
                        'userId': str(user_id) if user_id is not None else '',
                        'nameEng': name,
                        'nameBn': emp.get('nameBn', ''),
                        'email': emp.get('email', ''),
                        'designationEng': emp.get('designationEng', ''),
                        'mobile': emp.get('mobile', ''),
                        'status': emp.get('status', 'unknown'),
                        'photo': emp.get('photo', ''),
                    }
                    
                    if validated_employee['userId']:
                        validated_employees.append(validated_employee)
                        logger.debug(f" Added: {name} (ID: {validated_employee['userId']})")
                    else:
                        logger.warning(f"  Skipped {name} - missing userId (original: {user_id})")
                else:
                    logger.warning(f"  Invalid employee data at index {i}: {type(emp)}")
            
            logger.info(f" Returning {len(validated_employees)}/{len(employees)} validated employees for department {department_id}")
            
            # Log first few validated employee IDs for debugging
            if validated_employees:
                sample_validated = [f"{emp['nameEng']}({emp['userId']})" for emp in validated_employees[:3]]
                logger.info(f"📋 Sample validated employees: {sample_validated}")
            
            return validated_employees
            
        except Exception as e:
            logger.error(f" Failed to get employees for department {department_id}: {e}")
            import traceback
            logger.error(f" Traceback: {traceback.format_exc()}")
            raise PRPConnectionError(f"Employee retrieval failed: {str(e)}")
    
    def lookup_user_by_employee_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Enhanced debug version to find the employee search issue."""
        if not employee_id:
            return None
        
        try:
            logger.info(f"🔍 Starting search for employee: {employee_id}")
            departments = self.get_departments()
            logger.info(f"📋 Found {len(departments)} departments")
            
            # Log department details
            for i, dept in enumerate(departments[:5]):  # Log first 5 departments
                logger.info(f"📂 Dept {i+1}: {dept.get('nameEng')} (ID: {dept.get('id')})")
            
            for dept in departments:
                dept_id = dept.get('id')
                dept_name = dept.get('nameEng', 'Unknown')
                
                logger.info(f"🏢 Searching department: {dept_name} (ID: {dept_id})")
                
                try:
                    employees = self.get_department_employees(dept_id)
                    logger.info(f"👥 Found {len(employees)} employees in {dept_name}")
                    
                    # DEBUG: If no employees found, let's check the raw response
                    if len(employees) == 0:
                        logger.warning(f"⚠️  No employees in {dept_name} - checking raw API response...")
                        # Make direct API call to see raw response
                        try:
                            params = {'action': 'employee_details', 'departmentId': dept_id}
                            raw_response = self._make_authenticated_request('employee_details', params)
                            logger.info(f"📋 Raw API response for {dept_name}: {type(raw_response)}")
                            if isinstance(raw_response, dict):
                                logger.info(f"📋 Response keys: {list(raw_response.keys())}")
                                payload = raw_response.get('payload', [])
                                logger.info(f"📋 Payload type: {type(payload)}, length: {len(payload) if isinstance(payload, list) else 'N/A'}")
                                if isinstance(payload, list) and payload:
                                    sample_employee = payload[0]
                                    logger.info(f"📋 Sample employee structure: {type(sample_employee)}")
                                    if isinstance(sample_employee, dict):
                                        logger.info(f"📋 Sample employee keys: {list(sample_employee.keys())}")
                                        logger.info(f"📋 Sample userId: {sample_employee.get('userId')} (type: {type(sample_employee.get('userId'))})")
                        except Exception as debug_e:
                            logger.error(f"❌ Debug API call failed: {debug_e}")
                    else:
                        # Log sample employee IDs if we have employees
                        sample_ids = []
                        for emp in employees[:3]:
                            user_id = emp.get('userId', 'N/A')
                            name = emp.get('nameEng', 'Unknown')
                            sample_ids.append(f"{name}({user_id})")
                        logger.info(f"👤 Sample employees in {dept_name}: {sample_ids}")
                    
                    # Search for target employee
                    for employee in employees:
                        prp_user_id = str(employee.get('userId', ''))
                        employee_name = employee.get('nameEng', 'Unknown')
                        
                        logger.debug(f"🔍 Comparing: '{prp_user_id}' == '{employee_id}' for {employee_name}")
                        
                        if prp_user_id == str(employee_id):
                            logger.info(f"✅ MATCH FOUND! Employee {employee_id} ({employee_name}) in {dept_name}")
                            employee['department'] = dept
                            return employee
                            
                except Exception as e:
                    logger.error(f"❌ Error searching department {dept_name}: {e}")
                    import traceback
                    logger.error(f"❌ Traceback: {traceback.format_exc()}")
                    continue
            
            logger.warning(f"❌ Employee {employee_id} not found in any department after searching {len(departments)} departments")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lookup failed: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise PRPConnectionError(f"Employee lookup failed: {str(e)}")
    
    def convert_photo_to_django_file(self, photo_data: Union[bytes, str, None]) -> Optional[ContentFile]:
        """
        Convert PRP photo data (byte array) to Django ContentFile.
        
        Args:
            photo_data: Photo data from PRP API (byte array or base64 string)
            
        Returns:
            ContentFile: Django file object or None if conversion fails
        """
        if not photo_data:
            return None
        
        try:
            # Handle different photo data formats
            if isinstance(photo_data, str):
                # Assume base64 encoded string
                try:
                    photo_bytes = base64.b64decode(photo_data)
                except Exception as e:
                    logger.warning(f"⚠️  Failed to decode base64 photo: {e}")
                    return None
            elif isinstance(photo_data, (bytes, bytearray)):
                photo_bytes = bytes(photo_data)
            else:
                logger.warning(f"⚠️  Unsupported photo data type: {type(photo_data)}")
                return None
            
            # Create ContentFile for Django
            if photo_bytes:
                # Generate filename with timestamp
                filename = f"prp_photo_{int(timezone.now().timestamp())}.jpg"
                content_file = ContentFile(photo_bytes, name=filename)
                logger.debug(f"📸 Converted photo to Django file: {filename} ({len(photo_bytes)} bytes)")
                return content_file
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Photo conversion failed: {e}")
            return None
    
    def clear_cache(self):
        """Clear all PRP-related cached data."""
        cache_keys = [
            'prp_departments',
            'prp_departments_last_sync'
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        logger.info("🗑️  PRP cache cleared")


def create_prp_client() -> PRPClient:
    """
    Factory function to create PRP client with Django settings integration.
    
    This replaces the old mock client factory - now always returns real PRP client.
    
    Returns:
        PRPClient: Real PRP API client instance
    """
    logger.info("🏭 Creating REAL PRP client (NO MOCK DATA)")
    
    # Always create real client - no mock mode
    client = PRPClient(
        base_url=getattr(settings, 'PRP_BASE_URL', 'https://prp.parliament.gov.bd'),
        username=getattr(settings, 'PRP_USERNAME', 'ezzetech'),
        password=getattr(settings, 'PRP_PASSWORD', '${Fty#3a'),
        timeout=getattr(settings, 'PRP_TIMEOUT', 30),
        enable_caching=getattr(settings, 'PRP_ENABLE_CACHING', True)
    )
    
    logger.info("✅ Real PRP client created successfully")
    return client


# Export main classes
__all__ = [
    'PRPClient',
    'create_prp_client'
]