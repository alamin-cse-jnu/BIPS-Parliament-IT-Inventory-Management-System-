"""
Management Commands Package Initialization
==========================================

PIMS-PRP Integration Management Commands
Bangladesh Parliament Secretariat, Dhaka, Bangladesh

This package contains Django management commands for PRP (Parliament Resource Portal)
integration with PIMS (Parliament IT Inventory Management System).

Purpose: One-way sync PRP → PIMS (PRP is authoritative source)
Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
API Integration: https://prp.parliament.gov.bd

Available Commands:
------------------
1. sync_prp_users.py        - Sync employee data from PRP to PIMS
2. sync_prp_departments.py  - Sync department information from PRP 
3. debug_prp_connection.py  - Test and debug PRP API connectivity

Command Usage Examples:
----------------------
# Sync all users from PRP
python manage.py sync_prp_users

# Sync users from specific department
python manage.py sync_prp_users --department-id=1

# Sync departments from PRP  
python manage.py sync_prp_departments

# Test PRP API connection
python manage.py debug_prp_connection

Business Rules Implementation:
-----------------------------
- NO user creation from PIMS: All users originate from PRP
- One-way sync: PRP → PIMS (PRP is authoritative source) 
- Read-only PRP data: Information from PRP API cannot be edited in PIMS
- Admin sync control: Only admin can update/sync users from PRP
- Status management: PIMS admin inactive status takes precedence over PRP status
- Username generation: prp_{userId} format for Django username field
- Default password: "12345678" for all PRP-created users

PRP API Integration Details:
---------------------------
- Base URL: https://prp.parliament.gov.bd
- Authentication: Bearer token based
- Credentials: username="ezzetech", password="${Fty#3a"
- Key Endpoints:
  * Employee Details: /api/secure/external?action=employee_details&departmentId={departmentId}  
  * Departments: /api/secure/external?action=departments
  * Authentication: /api/authentication/external?action=token

Data Mapping Strategy:
---------------------
PRP API Data → PIMS CustomUser Fields:
- userId → employee_id
- nameEng → first_name + last_name (split)
- email → email  
- designationEng → designation
- department.nameEng → office
- mobile → phone_number
- photo → profile_image (converted)
- status → is_active + is_active_employee

Security Considerations:
-----------------------
- Secure token storage in Django settings
- Token refresh mechanism handled automatically
- Rate limiting for API calls
- Comprehensive error logging and audit trails
- Data integrity validation after each sync
- Admin-only command execution

Error Handling:
--------------
All commands implement comprehensive error handling for:
- PRP API connection failures
- Authentication errors
- Data validation issues
- Network timeouts and rate limiting
- Invalid response formats
- Database transaction failures

Logging:
--------
All operations are logged with appropriate levels:
- INFO: Successful operations and progress updates
- WARNING: Non-critical issues and data inconsistencies  
- ERROR: Failed operations and API errors
- DEBUG: Detailed debugging information (verbose mode)

Dependencies:
------------
- Django management command framework
- users.api.prp_client (PRP API client)
- users.api.sync_service (Business logic for sync)
- users.api.exceptions (Custom PRP exceptions)
- users.models.CustomUser (PIMS user model)

Command Development Guidelines:
------------------------------
1. Keep PRP integration separate from core PIMS functionality
2. Use existing Django patterns and conventions
3. Maintain backwards compatibility
4. Follow established error handling patterns
5. Implement comprehensive logging
6. Validate all input parameters
7. Handle Asia/Dhaka timezone properly
8. Provide detailed help text and usage examples

Testing Strategy:
----------------
- Test with existing PIMS users (non-PRP)
- Test PRP user creation and sync
- Test status management business rules
- Test command-line options and parameters
- Test error handling and recovery
- Test API connection failures
- Test data integrity validation

Success Criteria:
----------------
✅ Commands execute without breaking existing PIMS functionality
✅ PRP user data populates existing PIMS fields correctly
✅ Inactive PRP users become inactive in PIMS
✅ PIMS admin can override user status
✅ Comprehensive logging and error handling
✅ Commands are admin-controlled and audited
✅ Bangladesh/Dhaka timezone handling preserved
"""

# Package metadata for management commands
__version__ = '1.0.0'
__author__ = 'PIMS Development Team'
__location__ = 'Bangladesh Parliament Secretariat, Dhaka'
__description__ = 'PRP Integration Management Commands for PIMS'

# Import validation
import sys
from pathlib import Path

# Package information
PACKAGE_NAME = 'users.management.commands'
PACKAGE_PATH = Path(__file__).parent
COMMANDS_AVAILABLE = []

# Discover available command files
def _discover_commands():
    """
    Discover available PRP integration commands in this package.
    
    Returns:
        list: List of available command names
    """
    commands = []
    
    # Expected PRP integration commands
    expected_commands = [
        'sync_prp_users',
        'sync_prp_departments', 
        'debug_prp_connection'
    ]
    
    for command in expected_commands:
        command_file = PACKAGE_PATH / f'{command}.py'
        if command_file.exists():
            commands.append(command)
    
    return commands

# Initialize available commands list
COMMANDS_AVAILABLE = _discover_commands()

# Command validation and status
def get_command_status():
    """
    Get status of PRP integration commands.
    
    Returns:
        dict: Command availability status
    """
    status = {
        'package_initialized': True,
        'total_commands': len(COMMANDS_AVAILABLE),
        'available_commands': COMMANDS_AVAILABLE.copy(),
        'missing_commands': [],
        'integration_ready': False
    }
    
    # Check for missing essential commands
    essential_commands = ['sync_prp_users', 'sync_prp_departments']
    for cmd in essential_commands:
        if cmd not in COMMANDS_AVAILABLE:
            status['missing_commands'].append(cmd)
    
    # Check if integration is ready
    status['integration_ready'] = (
        len(status['missing_commands']) == 0 and 
        len(COMMANDS_AVAILABLE) >= 2
    )
    
    return status

def validate_dependencies():
    """
    Validate that required PRP integration modules are available.
    
    Returns:
        dict: Validation results
    """
    validation = {
        'success': True,
        'messages': [],
        'missing_modules': []
    }
    
    # Check PRP API modules
    required_modules = [
        'users.api.prp_client',
        'users.api.sync_service', 
        'users.api.exceptions'
    ]
    
    for module_name in required_modules:
        try:
            __import__(module_name)
            validation['messages'].append(f"✅ {module_name} - Available")
        except ImportError:
            validation['success'] = False
            validation['missing_modules'].append(module_name)
            validation['messages'].append(f"❌ {module_name} - Missing")
    
    # Check Django dependencies
    try:
        from django.core.management.base import BaseCommand
        validation['messages'].append("✅ Django management framework - Available")
    except ImportError:
        validation['success'] = False
        validation['messages'].append("❌ Django management framework - Missing")
    
    return validation

# Utility functions for command execution
def get_prp_logger(command_name=None):
    """
    Get logger instance for PRP commands.
    
    Args:
        command_name (str, optional): Name of the command for logging context
        
    Returns:
        logging.Logger: Configured logger instance
    """
    import logging
    
    logger_name = f'pims.prp_integration.commands'
    if command_name:
        logger_name += f'.{command_name}'
        
    return logging.getLogger(logger_name)

def get_default_prp_config():
    """
    Get default PRP configuration for commands.
    
    Returns:
        dict: Default PRP configuration
    """
    return {
        'base_url': 'https://prp.parliament.gov.bd',
        'username': 'ezzetech',
        'password': '${Fty#3a',
        'timeout': 30,
        'max_retries': 3,
        'batch_size': 100,
        'location': 'Bangladesh Parliament Secretariat, Dhaka'
    }

# Export commonly used functions and variables
__all__ = [
    '__version__',
    '__author__', 
    '__location__',
    '__description__',
    'PACKAGE_NAME',
    'COMMANDS_AVAILABLE',
    'get_command_status',
    'validate_dependencies',
    'get_prp_logger',
    'get_default_prp_config'
]

# Initialize package and log status
if __name__ != '__main__':
    # Only run during import, not direct execution
    logger = get_prp_logger('init')
    status = get_command_status()
    
    logger.debug(f"📦 PRP Commands package initialized")
    logger.debug(f"🏢 Location: {__location__}")
    logger.debug(f"📋 Available commands: {len(status['available_commands'])}")
    
    if status['integration_ready']:
        logger.info("✅ PRP integration commands ready")
    else:
        logger.warning(f"⚠️ Missing commands: {status['missing_commands']}")

# Command execution helper
def execute_command_safely(command_class, *args, **kwargs):
    """
    Execute a PRP command with proper error handling.
    
    Args:
        command_class: Django management command class
        *args: Command arguments
        **kwargs: Command keyword arguments
        
    Returns:
        dict: Execution result with success status and messages
    """
    import traceback
    
    result = {
        'success': False,
        'messages': [],
        'errors': []
    }
    
    logger = get_prp_logger('executor')
    
    try:
        # Validate dependencies before execution
        validation = validate_dependencies()
        if not validation['success']:
            result['errors'].extend(validation['messages'])
            return result
        
        # Execute command
        command_instance = command_class()
        command_instance.handle(*args, **kwargs)
        
        result['success'] = True
        result['messages'].append("Command executed successfully")
        
    except ImportError as e:
        error_msg = f"Missing dependencies: {str(e)}"
        result['errors'].append(error_msg)
        logger.error(error_msg)
        
    except Exception as e:
        error_msg = f"Command execution failed: {str(e)}"
        result['errors'].append(error_msg)
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
    
    return result

# Add helper to __all__
__all__.append('execute_command_safely')