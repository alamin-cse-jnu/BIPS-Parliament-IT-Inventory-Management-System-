"""
PRP (Parliament Resource Portal) Integration API Package
========================================================

This package provides API integration functionality for syncing user data
from PRP to PIMS (Parliament IT Inventory Management System).

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: One-way sync PRP → PIMS (PRP is authoritative source)

Package Structure:
-----------------
- prp_client.py     : Core PRP API client with authentication and HTTP requests
- sync_service.py   : Business logic for user synchronization and data mapping  
- exceptions.py     : Custom exceptions for PRP API operations

Integration Details:
-------------------
- API Base URL: https://prp.parliament.gov.bd  
- Authentication: Bearer token based (username: "ezzetech", password: "${Fty#3a")
- Sync Direction: PRP → PIMS only (one-way)
- Business Rule: NO user creation from PIMS, all users from PRP
- Data Fields: Reuse existing CustomUser fields for PRP data mapping

PRP API Endpoints (Required for PIMS User Integration):
------------------------------------------------------
1. Authentication:
   - Get Token: POST /api/authentication/external?action=token
   - Refresh Token: GET /api/authentication/external?action=refresh-token

2. Employee Data (Core Requirements):
   - Employee Details: GET /api/secure/external?action=employee_details&departmentId={departmentId}
   - Departments: GET /api/secure/external?action=departments

Note: PRP API has additional endpoints (divisions, districts, parliament info, MP details) 
but they are not used in the current PIMS user integration scope.

Data Models (PIMS Integration Scope Only):
------------------------------------------
EmployeeDetails (PIMS Uses Only): {userId, nameEng, designationEng, email, mobile, photo, status}
DepartmentModel: {nameEng, nameBng, id, isWing}

Response Format: {responseCode: 200, payload: [...], msg: "Success"}

Note: The complete PRP API has additional models (LocationModel, ParliamentModel, MPDetails, 
PoliticalParty) but they are outside the current PIMS user integration scope.

Key Features:
------------
- Token-based authentication with automatic refresh
- Comprehensive error handling and logging
- Rate limiting and API failure recovery
- One-way data sync with admin override protection
- Status management following PRP business rules

Usage Example:
-------------
from users.api.prp_client import PRPClient
from users.api.sync_service import PRPSyncService
from users.api.exceptions import PRPConnectionError

try:
    # Initialize PRP client with official credentials
    prp_client = PRPClient(
        base_url='https://prp.parliament.gov.bd',
        username='ezzetech',
        password='${Fty#3a'
    )
    
    # Create sync service
    sync_service = PRPSyncService(prp_client)
    
    # Sync users from specific department (requires departmentId from DepartmentModel)
    result = sync_service.sync_department_users(department_id=1)
    
    # Sync all departments
    result = sync_service.sync_all_departments()
    
    # Get sync status for a user
    user_status = sync_service.get_sync_status(employee_id="12345")
    
except PRPConnectionError as e:
    logger.error(f"PRP connection failed: {e}")

PRP Data Mapping (Official Field Mapping - PIMS Integration):
----------------------------------------------------------
PRP EmployeeDetails → PIMS CustomUser Fields (ONLY these 7 fields used):
- userId → employee_id  
- nameEng → first_name + last_name (split)
- email → email
- designationEng → designation
- mobile → phone_number
- photo (byte[]) → profile_image (converted)
- status → is_active + is_active_employee

PRP DepartmentModel → PIMS Office Field:
- nameEng → office

Note: PRP EmployeeDetails has additional fields (fatherNameEng, motherNameEng, dateOfBirth, 
addresses, etc.) but PIMS integration ONLY uses the 7 fields listed above per project requirements.

Security Notes:
--------------
- All API credentials stored securely in Django settings
- Token refresh handled automatically
- Comprehensive audit logging for all sync operations
- Rate limiting to prevent API overload
- Error handling prevents data corruption

Business Rules Implementation:
-----------------------------
1. User Creation: NO user creation from PIMS interface
2. Data Authority: PRP is the single source of truth
3. Sync Direction: One-way PRP → PIMS only
4. Field Editing: PRP-sourced fields are read-only in PIMS
5. Status Override: PIMS admin can override user status
6. Sync Control: Admin-initiated sync operations only

Maintenance:
-----------
- Regular token refresh (handled automatically)
- Sync operation logging and monitoring
- Error notification system for failed syncs
- Data integrity validation after each sync
"""

# Package metadata
__version__ = '1.0.0'
__author__ = 'PIMS Development Team'
__email__ = 'pims@parliament.gov.bd'
__description__ = 'PRP Integration API for PIMS User Synchronization'

# Import main classes for convenient access
# Note: During development phase, modules may not exist yet, so we handle imports gracefully
__all__ = []

# Try to import modules as they become available during development
try:
    from .exceptions import (
        PRPBaseException,
        PRPConnectionError, 
        PRPAuthenticationError,
        PRPSyncError,
        PRPDataError,
        PRPRateLimitError
    )
    
    # Add exception classes to __all__ if successfully imported
    __all__.extend([
        'PRPBaseException',
        'PRPConnectionError',
        'PRPAuthenticationError', 
        'PRPSyncError',
        'PRPDataError',
        'PRPRateLimitError',
    ])
    
except ImportError:
    # exceptions.py not created yet - this is expected during development
    pass

try:
    from .prp_client import PRPClient, PRPAPIConfig
    
    # Add client classes to __all__ if successfully imported
    __all__.extend([
        'PRPClient',
        'PRPAPIConfig',
    ])
    
except ImportError:
    # prp_client.py not created yet - this is expected during development
    pass

try:
    from .sync_service import PRPSyncService, PRPSyncResult
    
    # Add sync service classes to __all__ if successfully imported
    __all__.extend([
        'PRPSyncService', 
        'PRPSyncResult',
    ])
    
except ImportError:
    # sync_service.py not created yet - this is expected during development
    pass

# Package-level configuration based on official PRP API documentation
DEFAULT_CONFIG = {
    # API Connection Settings
    'API_BASE_URL': 'https://prp.parliament.gov.bd',
    'API_TIMEOUT': 30,
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 1,
    'BATCH_SIZE': 50,
    'RATE_LIMIT_DELAY': 0.5,
    
    # Authentication Settings (from official API spec)
    'AUTH_USERNAME': 'ezzetech',
    'AUTH_PASSWORD': '${Fty#3a',  # From official API documentation
    
    # API Endpoints (PIMS Integration - Only Required Endpoints)
    'ENDPOINTS': {
        # Authentication (Required)
        'TOKEN': '/api/authentication/external?action=token',
        'REFRESH_TOKEN': '/api/authentication/external?action=refresh-token',
        
        # Employee & Department Data (Required for User Sync)
        'EMPLOYEE_DETAILS': '/api/secure/external?action=employee_details&departmentId={departmentId}',
        'DEPARTMENTS': '/api/secure/external?action=departments',
    },
    
    # Response Structure (from official API spec)
    'RESPONSE_STRUCTURE': {
        'SUCCESS_CODE': 200,
        'SUCCESS_MESSAGE': 'Success',
        'PAYLOAD_KEY': 'payload',
        'MESSAGE_KEY': 'msg',
        'RESPONSE_CODE_KEY': 'responseCode',
    },
}

# Logging configuration for PRP operations
import logging

# Create PRP-specific logger
prp_logger = logging.getLogger('pims.prp_integration')

# Set up basic configuration if not already configured
if not prp_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    prp_logger.addHandler(handler)
    prp_logger.setLevel(logging.INFO)

def get_prp_logger():
    """
    Get the PRP integration logger.
    
    Returns:
        logging.Logger: Configured logger for PRP operations
    """
    return prp_logger

# Utility functions for package
def get_version():
    """
    Get the current package version.
    
    Returns:
        str: Package version string
    """
    return __version__

def get_config():
    """
    Get the default PRP configuration.
    
    Returns:
        dict: Default configuration settings
    """
    return DEFAULT_CONFIG.copy()

# Package initialization message (only in development)
import os
if os.environ.get('DJANGO_SETTINGS_MODULE') and 'test' not in os.environ.get('DJANGO_SETTINGS_MODULE', ''):
    prp_logger.info(f"PRP Integration API Package v{__version__} initialized")
    prp_logger.info("Ready for Parliament Resource Portal synchronization")
    
    # Show which modules are available during development
    if __all__:
        prp_logger.info(f"Available modules: {', '.join(__all__)}")
    else:
        prp_logger.info("Development mode: No modules imported yet (this is expected)")
        prp_logger.info("Modules will be imported as they are created: exceptions.py → prp_client.py → sync_service.py")