"""
Users App Initialization
Bangladesh Parliament Secretariat IT Inventory Management System
Location: Dhaka, Bangladesh

This module initializes the users app with proper configuration for:
- Custom user model integration
- PRP (Parliament Resource Portal) integration
- Context processors
- Template system integration
"""

default_app_config = 'users.apps.UsersConfig'

# Version information
__version__ = '1.0.0'
__author__ = 'PIMS Development Team'
__location__ = 'Bangladesh Parliament Secretariat, Dhaka'

# App metadata
APP_NAME = 'users'
APP_VERBOSE_NAME = 'User Management'
APP_DESCRIPTION = 'User authentication, profiles, and PRP integration for PIMS'

# PRP Integration Status
PRP_INTEGRATION_AVAILABLE = False

try:
    from django.conf import settings
    PRP_INTEGRATION_AVAILABLE = getattr(settings, 'PRP_INTEGRATION_AVAILABLE', False)
except ImportError:
    # Settings not available during app loading
    pass

# Export commonly used components
__all__ = [
    'default_app_config',
    'APP_NAME',
    'APP_VERBOSE_NAME', 
    'APP_DESCRIPTION',
    'PRP_INTEGRATION_AVAILABLE',
]