"""
Users Management Package Initialization
=======================================

PIMS Users Management with PRP Integration Support
Bangladesh Parliament Secretariat, Dhaka, Bangladesh

This package provides Django management functionality for the users app with 
integrated PRP (Parliament Resource Portal) synchronization capabilities.

Purpose: Centralized user management with real PRP API integration
Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
API Integration: https://prp.parliament.gov.bd

Package Structure:
-----------------
users/management/
├── __init__.py                    # This file - Package initialization
└── commands/                      # Django management commands
    ├── __init__.py               # Commands package initialization
    ├── sync_prp_users.py        # Sync employee data from PRP to PIMS
    ├── sync_prp_departments.py  # Sync department information from PRP
    └── debug_prp_connection.py  # Test and debug PRP API connectivity

Key Features:
------------
1. **Real PRP API Integration**: No mock data - actual employee data from PRP
2. **One-way Synchronization**: PRP → PIMS (PRP is authoritative source)
3. **Admin-controlled Operations**: Only admin can trigger sync operations
4. **Comprehensive Logging**: All operations logged for audit and debugging
5. **Error Handling**: Robust error handling and recovery mechanisms
6. **Data Integrity**: Validation and consistency checks

Business Rules Implementation:
-----------------------------
- NO user creation from PIMS: All users originate from PRP
- One-way sync: PRP → PIMS only (PRP is single source of truth)
- Read-only PRP data: Information from PRP API cannot be edited in PIMS
- Admin sync control: Only admin can update/sync users from PRP
- Status management: PIMS admin inactive status takes precedence over PRP status
- Username generation: prp_{userId} format for Django username field
- Default password: "12345678" for all PRP-created users

PRP Integration Details:
-----------------------
- Base URL: https://prp.parliament.gov.bd
- Authentication: Bearer token based
- Credentials: username="ezzetech", password="${Fty#3a"
- Token refresh: Automatic token refresh mechanism
- Rate limiting: Built-in API rate limiting protection

Data Mapping Strategy:
---------------------
PRP API Data → PIMS CustomUser Fields:
- userId → employee_id (unique identifier)
- nameEng → first_name + last_name (split full name)
- email → email (contact information)
- designationEng → designation (job title)
- department.nameEng → office (department mapping)
- mobile → phone_number (contact number)
- photo (byte[]) → profile_image (converted image)
- status → is_active + is_active_employee (user status)

Security Considerations:
-----------------------
- Secure token storage in Django settings
- Token refresh handled automatically
- Rate limiting for API calls
- Comprehensive error logging and audit trails
- Data integrity validation after each sync
- Admin-only command execution with proper permissions

Management Commands Available:
-----------------------------
1. **sync_prp_users**
   - Sync employee data from PRP to PIMS
   - Usage: python manage.py sync_prp_users
   - Options: --department-id, --verbose, --dry-run

2. **sync_prp_departments**
   - Sync department information from PRP
   - Usage: python manage.py sync_prp_departments
   - Options: --verbose, --force, --export

3. **debug_prp_connection**
   - Test and debug PRP API connectivity
   - Usage: python manage.py debug_prp_connection
   - Options: --test-auth, --test-endpoints, --verbose

Error Handling Strategy:
-----------------------
All management operations implement comprehensive error handling for:
- PRP API connection failures
- Authentication token errors
- Network timeouts and rate limiting
- Invalid response formats from PRP
- Data validation and integrity issues
- Database transaction failures
- Image processing errors (for profile photos)

Logging Configuration:
---------------------
All operations are logged with appropriate levels:
- INFO: Successful operations and progress updates
- WARNING: Non-critical issues and data inconsistencies
- ERROR: Failed operations and API errors
- DEBUG: Detailed debugging information (verbose mode)

Log Location: Asia/Dhaka timezone for all timestamps
Log Format: Includes operation context, user info, and detailed error messages

Dependencies:
------------
- Django management command framework (django.core.management)
- users.api.prp_client (PRP API client functionality)
- users.api.sync_service (Business logic for synchronization)
- users.api.exceptions (Custom PRP integration exceptions)
- users.models.CustomUser (PIMS user model)

Development Guidelines:
----------------------
1. Keep PRP integration separate from core PIMS functionality
2. Use existing Django patterns and conventions
3. Maintain backwards compatibility with existing PIMS users
4. Follow established error handling patterns
5. Implement comprehensive logging for all operations
6. Validate all input parameters and API responses
7. Handle Asia/Dhaka timezone properly for all timestamps
8. Provide detailed help text and usage examples

Testing Strategy:
----------------
- Test with existing PIMS users (non-PRP managed)
- Test PRP user creation and synchronization
- Test status management business rules
- Test command-line options and parameters
- Test error handling and recovery mechanisms
- Test API connection failures and timeouts
- Test data integrity validation
- Test timezone handling for Bangladesh location

Monitoring and Maintenance:
--------------------------
- Regular monitoring of sync operation success rates
- Automatic token refresh validation
- API endpoint health checking
- Data consistency validation
- Performance monitoring for large datasets
- Error notification system for critical failures
- Regular backup of sync operation logs

Success Criteria:
----------------
✅ Real PRP API integration (no mock data)
✅ Users can login with PRP User ID and default password
✅ PRP user data populates existing PIMS fields correctly
✅ Inactive PRP users become inactive in PIMS
✅ PIMS admin can override user status
✅ PRP-sourced fields are read-only in PIMS interface
✅ Sync operations are admin-controlled and logged
✅ No breaking changes to existing PIMS functionality
✅ Minimal database schema changes (2 new fields only)
✅ Existing templates continue working with mixed user types
✅ Bangladesh/Dhaka timezone handling preserved
"""

# Package metadata
__version__ = '1.0.0'
__author__ = 'PIMS Development Team'
__location__ = 'Bangladesh Parliament Secretariat, Dhaka'
__description__ = 'Users Management with PRP Integration for PIMS'

# Import required modules
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Package information
PACKAGE_NAME = 'users.management'
PACKAGE_PATH = Path(__file__).parent
MANAGEMENT_AVAILABLE = True

# PRP Integration status
PRP_INTEGRATION_READY = False

try:
    # Check if PRP integration modules are available
    from users.api.prp_client import PRPClient, create_prp_client
    from users.api.sync_service import PRPSyncService
    from users.api.exceptions import PRPException, PRPConnectionError
    PRP_INTEGRATION_READY = True
except ImportError:
    # PRP integration not available - this is acceptable for development
    pass

# Django management framework availability
DJANGO_MANAGEMENT_AVAILABLE = False

try:
    from django.core.management.base import BaseCommand, CommandError
    from django.core.management import call_command
    DJANGO_MANAGEMENT_AVAILABLE = True
except ImportError:
    # Django not available during package import
    pass

# Configure logging for management operations
def get_management_logger(operation_name=None):
    """
    Get logger instance for management operations.
    
    Args:
        operation_name (str, optional): Name of the operation for logging context
        
    Returns:
        logging.Logger: Configured logger instance with proper formatting
    """
    logger_name = f'pims.users.management'
    if operation_name:
        logger_name += f'.{operation_name}'
        
    logger = logging.getLogger(logger_name)
    
    # Configure logger if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [Dhaka] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger

# Management package status
def get_package_status():
    """
    Get comprehensive status of the management package.
    
    Returns:
        dict: Package status information
    """
    status = {
        'package_initialized': True,
        'location': __location__,
        'version': __version__,
        'django_available': DJANGO_MANAGEMENT_AVAILABLE,
        'prp_integration_ready': PRP_INTEGRATION_READY,
        'commands_available': [],
        'missing_dependencies': [],
        'integration_health': 'unknown'
    }
    
    # Check for available commands
    commands_dir = PACKAGE_PATH / 'commands'
    if commands_dir.exists():
        expected_commands = [
            'sync_prp_users.py',
            'sync_prp_departments.py',
            'debug_prp_connection.py'
        ]
        
        for cmd_file in expected_commands:
            cmd_path = commands_dir / cmd_file
            if cmd_path.exists():
                cmd_name = cmd_file.replace('.py', '')
                status['commands_available'].append(cmd_name)
    
    # Check dependencies
    if not DJANGO_MANAGEMENT_AVAILABLE:
        status['missing_dependencies'].append('django.core.management')
    
    if not PRP_INTEGRATION_READY:
        status['missing_dependencies'].append('users.api (PRP integration)')
    
    # Determine integration health
    if len(status['commands_available']) >= 3 and PRP_INTEGRATION_READY:
        status['integration_health'] = 'healthy'
    elif len(status['commands_available']) >= 2:
        status['integration_health'] = 'partial'
    else:
        status['integration_health'] = 'needs_setup'
    
    return status

# Validate management package setup
def validate_setup():
    """
    Validate that the management package is properly set up.
    
    Returns:
        dict: Validation results with success status and detailed messages
    """
    validation = {
        'success': True,
        'messages': [],
        'warnings': [],
        'errors': []
    }
    
    logger = get_management_logger('validation')
    
    # Check Django management framework
    if DJANGO_MANAGEMENT_AVAILABLE:
        validation['messages'].append("✅ Django management framework - Available")
    else:
        validation['success'] = False
        validation['errors'].append("❌ Django management framework - Not available")
    
    # Check PRP integration
    if PRP_INTEGRATION_READY:
        validation['messages'].append("✅ PRP integration modules - Available")
    else:
        validation['warnings'].append("⚠️ PRP integration modules - Not available (acceptable for development)")
    
    # Check commands directory
    commands_dir = PACKAGE_PATH / 'commands'
    if commands_dir.exists():
        validation['messages'].append("✅ Commands directory - Available")
        
        # Check individual command files
        essential_commands = ['sync_prp_users.py', 'sync_prp_departments.py']
        optional_commands = ['debug_prp_connection.py']
        
        for cmd_file in essential_commands:
            cmd_path = commands_dir / cmd_file
            if cmd_path.exists():
                validation['messages'].append(f"✅ {cmd_file} - Available")
            else:
                validation['success'] = False
                validation['errors'].append(f"❌ {cmd_file} - Missing (essential)")
        
        for cmd_file in optional_commands:
            cmd_path = commands_dir / cmd_file
            if cmd_path.exists():
                validation['messages'].append(f"✅ {cmd_file} - Available")
            else:
                validation['warnings'].append(f"⚠️ {cmd_file} - Missing (optional)")
    else:
        validation['success'] = False
        validation['errors'].append("❌ Commands directory - Missing")
    
    # Log validation results
    if validation['success']:
        logger.info("✅ Management package validation successful")
    else:
        logger.error("❌ Management package validation failed")
        for error in validation['errors']:
            logger.error(error)
    
    for warning in validation['warnings']:
        logger.warning(warning)
    
    return validation

# Get default configuration for PRP operations
def get_default_config():
    """
    Get default configuration for PRP management operations.
    
    Returns:
        dict: Default configuration dictionary
    """
    return {
        'prp_base_url': 'https://prp.parliament.gov.bd',
        'prp_username': 'ezzetech',
        'prp_password': '${Fty#3a',
        'location': 'Bangladesh Parliament Secretariat, Dhaka',
        'timezone': 'Asia/Dhaka',
        'default_password': '12345678',
        'username_prefix': 'prp_',
        'batch_size': 100,
        'timeout': 30,
        'max_retries': 3,
        'rate_limit_delay': 1.0,
        'token_refresh_threshold': 300  # 5 minutes
    }

# Create PRP client instance for management operations
def create_management_prp_client():
    """
    Create PRP client instance configured for management operations.
    
    Returns:
        PRPClient: Configured PRP client instance
        
    Raises:
        ImportError: If PRP integration modules are not available
        PRPConnectionError: If connection to PRP API fails
    """
    if not PRP_INTEGRATION_READY:
        raise ImportError(
            "PRP integration modules not available. "
            "Ensure users.api.prp_client and related modules are implemented."
        )
    
    logger = get_management_logger('prp_client')
    config = get_default_config()
    
    try:
        logger.info(f"🏢 Creating PRP client for {config['location']}")
        
        prp_client = create_prp_client(
            base_url=config['prp_base_url'],
            username=config['prp_username'],
            password=config['prp_password']
        )
        
        logger.info("✅ PRP client created successfully")
        return prp_client
        
    except Exception as e:
        logger.error(f"❌ Failed to create PRP client: {str(e)}")
        raise

# Execute management command safely
def execute_command_safely(command_name, *args, **kwargs):
    """
    Execute a Django management command with proper error handling.
    
    Args:
        command_name (str): Name of the management command
        *args: Command arguments
        **kwargs: Command keyword arguments
        
    Returns:
        dict: Execution result with success status and messages
    """
    if not DJANGO_MANAGEMENT_AVAILABLE:
        return {
            'success': False,
            'error': 'Django management framework not available',
            'messages': []
        }
    
    logger = get_management_logger('executor')
    result = {
        'success': False,
        'messages': [],
        'errors': [],
        'command': command_name
    }
    
    try:
        logger.info(f"🔧 Executing management command: {command_name}")
        
        # Validate command exists
        commands_dir = PACKAGE_PATH / 'commands'
        command_file = commands_dir / f'{command_name}.py'
        
        if not command_file.exists():
            result['errors'].append(f"Command file {command_name}.py not found")
            return result
        
        # Execute command using Django's call_command
        call_command(command_name, *args, **kwargs)
        
        result['success'] = True
        result['messages'].append(f"Command {command_name} executed successfully")
        logger.info(f"✅ Command {command_name} completed successfully")
        
    except CommandError as e:
        error_msg = f"Django command error: {str(e)}"
        result['errors'].append(error_msg)
        logger.error(f"❌ {error_msg}")
        
    except Exception as e:
        error_msg = f"Unexpected error executing {command_name}: {str(e)}"
        result['errors'].append(error_msg)
        logger.error(f"❌ {error_msg}")
    
    return result

# Health check for management operations
def health_check():
    """
    Perform comprehensive health check for management operations.
    
    Returns:
        dict: Health check results
    """
    logger = get_management_logger('health_check')
    
    health = {
        'status': 'unknown',
        'timestamp': None,
        'location': __location__,
        'checks': {
            'package_status': None,
            'validation_status': None,
            'prp_connection': None,
            'commands_availability': None
        },
        'summary': {
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0,
            'warnings': 0
        }
    }
    
    try:
        from django.utils import timezone
        health['timestamp'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')
    except ImportError:
        from datetime import datetime
        health['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    logger.info("🏥 Starting management package health check...")
    
    # Check package status
    try:
        package_status = get_package_status()
        health['checks']['package_status'] = {
            'status': 'pass' if package_status['integration_health'] != 'needs_setup' else 'fail',
            'details': package_status
        }
        health['summary']['total_checks'] += 1
        if health['checks']['package_status']['status'] == 'pass':
            health['summary']['passed_checks'] += 1
        else:
            health['summary']['failed_checks'] += 1
    except Exception as e:
        health['checks']['package_status'] = {
            'status': 'fail',
            'error': str(e)
        }
        health['summary']['total_checks'] += 1
        health['summary']['failed_checks'] += 1
    
    # Check validation
    try:
        validation = validate_setup()
        health['checks']['validation_status'] = {
            'status': 'pass' if validation['success'] else 'fail',
            'details': validation
        }
        health['summary']['total_checks'] += 1
        if health['checks']['validation_status']['status'] == 'pass':
            health['summary']['passed_checks'] += 1
        else:
            health['summary']['failed_checks'] += 1
        
        health['summary']['warnings'] += len(validation.get('warnings', []))
    except Exception as e:
        health['checks']['validation_status'] = {
            'status': 'fail',
            'error': str(e)
        }
        health['summary']['total_checks'] += 1
        health['summary']['failed_checks'] += 1
    
    # Check PRP connection (if available)
    if PRP_INTEGRATION_READY:
        try:
            # This is a basic check - actual connection testing would be done by debug_prp_connection command
            prp_client = create_management_prp_client()
            health['checks']['prp_connection'] = {
                'status': 'pass',
                'details': 'PRP client created successfully'
            }
            health['summary']['total_checks'] += 1
            health['summary']['passed_checks'] += 1
        except Exception as e:
            health['checks']['prp_connection'] = {
                'status': 'fail',
                'error': str(e)
            }
            health['summary']['total_checks'] += 1
            health['summary']['failed_checks'] += 1
    else:
        health['checks']['prp_connection'] = {
            'status': 'skip',
            'reason': 'PRP integration modules not available'
        }
        health['summary']['warnings'] += 1
    
    # Check commands availability
    try:
        commands_dir = PACKAGE_PATH / 'commands'
        available_commands = []
        if commands_dir.exists():
            for cmd_file in commands_dir.glob('*.py'):
                if cmd_file.name != '__init__.py':
                    available_commands.append(cmd_file.stem)
        
        health['checks']['commands_availability'] = {
            'status': 'pass' if len(available_commands) >= 2 else 'fail',
            'details': {
                'available_commands': available_commands,
                'total_commands': len(available_commands)
            }
        }
        health['summary']['total_checks'] += 1
        if health['checks']['commands_availability']['status'] == 'pass':
            health['summary']['passed_checks'] += 1
        else:
            health['summary']['failed_checks'] += 1
    except Exception as e:
        health['checks']['commands_availability'] = {
            'status': 'fail',
            'error': str(e)
        }
        health['summary']['total_checks'] += 1
        health['summary']['failed_checks'] += 1
    
    # Determine overall status
    if health['summary']['failed_checks'] == 0:
        health['status'] = 'healthy'
    elif health['summary']['passed_checks'] > health['summary']['failed_checks']:
        health['status'] = 'degraded'
    else:
        health['status'] = 'unhealthy'
    
    logger.info(f"🏥 Health check completed - Status: {health['status']}")
    logger.info(f"📊 Results: {health['summary']['passed_checks']}/{health['summary']['total_checks']} checks passed")
    
    return health

# Export commonly used functions and variables
__all__ = [
    '__version__',
    '__author__',
    '__location__',
    '__description__',
    'PACKAGE_NAME',
    'MANAGEMENT_AVAILABLE',
    'PRP_INTEGRATION_READY',
    'get_management_logger',
    'get_package_status',
    'validate_setup',
    'get_default_config',
    'create_management_prp_client',
    'execute_command_safely',
    'health_check'
]

# Initialize package on import
if __name__ != '__main__':
    # Only run during import, not direct execution
    logger = get_management_logger('init')
    
    logger.info(f"📦 Users management package initialized")
    logger.info(f"🏢 Location: {__location__}")
    logger.info(f"🔧 Django management: {'Available' if DJANGO_MANAGEMENT_AVAILABLE else 'Not available'}")
    logger.info(f"🔗 PRP integration: {'Ready' if PRP_INTEGRATION_READY else 'Not available'}")
    
    # Log package status
    try:
        status = get_package_status()
        logger.info(f"📋 Commands available: {len(status['commands_available'])}")
        logger.info(f"🏥 Integration health: {status['integration_health']}")
        
        if status['integration_health'] == 'healthy':
            logger.info("✅ Management package ready for PRP operations")
        elif status['integration_health'] == 'partial':
            logger.warning("⚠️ Partial functionality - some commands may not be available")
        else:
            logger.warning("⚠️ Setup incomplete - run health_check() for details")
    except Exception as e:
        logger.error(f"❌ Error during package initialization: {str(e)}")

# Cleanup function for graceful shutdown
def cleanup():
    """
    Cleanup function for graceful package shutdown.
    Called during application shutdown or testing cleanup.
    """
    logger = get_management_logger('cleanup')
    logger.info("🧹 Users management package cleanup completed")
    
# Add cleanup to __all__
__all__.append('cleanup')
--