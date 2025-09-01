# users/api/__init__.py
# PIMS-PRP Integration API Module
# Location: Bangladesh Parliament Secretariat, Dhaka
# 
# This module provides API integration capabilities for connecting PIMS
# with the Parliament Resource Portal (PRP) system.
# ============================================================================

"""
PIMS-PRP API Integration Module
===============================

This package contains all PRP (Parliament Resource Portal) API integration
components for the PIMS (Parliament IT Inventory Management System).

Key Components:
- prp_client.py: Low-level API client for PRP communication
- sync_service.py: Business logic for synchronizing user data
- exceptions.py: Custom exception classes for PRP operations

Location: Bangladesh Parliament Secretariat, Dhaka
All operations maintain Asia/Dhaka timezone consistency.
"""

__version__ = '1.0.0'
__author__ = 'PIMS Development Team'
__location__ = 'Bangladesh Parliament Secretariat, Dhaka'

# Import key classes for easy access
try:
    from .prp_client import PRPClient
    from .sync_service import PRPSyncService
    from .exceptions import (
        PRPException,
        PRPConnectionError,
        PRPAuthenticationError,
        PRPDataError,
        PRPConfigurationError,
        PRPBusinessRuleError
    )
    
    # API availability flag
    PRP_API_AVAILABLE = True
    
    __all__ = [
        'PRPClient',
        'PRPSyncService', 
        'PRPException',
        'PRPConnectionError',
        'PRPAuthenticationError',
        'PRPDataError',
        'PRPConfigurationError',
        'PRPBusinessRuleError',
        'PRP_API_AVAILABLE'
    ]

except ImportError as e:
    # Handle case where PRP dependencies are not available
    import logging
    
    logger = logging.getLogger(__name__)
    logger.warning(f"PRP API components not available: {e}")
    logger.warning("PRP integration will be disabled")
    
    # Provide stub implementations to prevent import errors
    class PRPClientStub:
        """Stub implementation when PRP client is not available."""
        
        def __init__(self, *args, **kwargs):
            raise ImportError("PRP API client not available - missing dependencies")
    
    class PRPSyncServiceStub:
        """Stub implementation when PRP sync service is not available."""
        
        def __init__(self, *args, **kwargs):
            raise ImportError("PRP sync service not available - missing dependencies")
    
    # Export stub classes
    PRPClient = PRPClientStub
    PRPSyncService = PRPSyncServiceStub
    
    # Generic exception for when PRP is not available
    class PRPNotAvailableError(Exception):
        """Raised when PRP functionality is requested but not available."""
        pass
    
    PRPException = PRPNotAvailableError
    PRPConnectionError = PRPNotAvailableError
    PRPAuthenticationError = PRPNotAvailableError
    PRPDataError = PRPNotAvailableError
    PRPConfigurationError = PRPNotAvailableError
    PRPBusinessRuleError = PRPNotAvailableError
    
    # API availability flag
    PRP_API_AVAILABLE = False
    
    __all__ = [
        'PRPClient',
        'PRPSyncService',
        'PRPException',
        'PRPConnectionError', 
        'PRPAuthenticationError',
        'PRPDataError',
        'PRPConfigurationError',
        'PRPBusinessRuleError',
        'PRP_API_AVAILABLE',
        'PRPNotAvailableError'
    ]

# Configuration validation helper
def validate_prp_configuration():
    """
    Validate PRP configuration is properly set up.
    
    Returns:
        bool: True if PRP configuration is valid, False otherwise
    """
    if not PRP_API_AVAILABLE:
        return False
    
    try:
        from django.conf import settings
        
        # Check required settings exist
        prp_settings = getattr(settings, 'PRP_API_SETTINGS', {})
        required_settings = ['BASE_URL', 'AUTH_USERNAME', 'AUTH_PASSWORD']
        
        for setting in required_settings:
            if not prp_settings.get(setting):
                return False
        
        return True
        
    except Exception:
        return False

# Auto-validation on import (in development)
def _auto_validate():
    """Auto-validate PRP configuration during import."""
    try:
        from django.conf import settings
        
        if getattr(settings, 'DEBUG', False):
            is_valid = validate_prp_configuration()
            if PRP_API_AVAILABLE and not is_valid:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "🚨 PRP API is available but configuration is incomplete. "
                    "Check PRP_API_SETTINGS in your Django settings."
                )
    except Exception:
        pass  # Ignore validation errors during import

# Run auto-validation
_auto_validate()

# Module information for debugging
def get_module_info():
    """Get information about this API module."""
    return {
        'version': __version__,
        'author': __author__,
        'location': __location__,
        'api_available': PRP_API_AVAILABLE,
        'configuration_valid': validate_prp_configuration() if PRP_API_AVAILABLE else False,
        'components': __all__
    }

# Development helper
def print_module_status():
    """Print module status for debugging (development only)."""
    info = get_module_info()
    print("\n" + "="*60)
    print("🏛️  PIMS-PRP API Module Status")
    print("="*60)
    print(f"Location: {info['location']}")
    print(f"Version: {info['version']}")
    print(f"API Available: {'✅' if info['api_available'] else '❌'}")
    print(f"Configuration Valid: {'✅' if info['configuration_valid'] else '❌'}")
    print(f"Components Loaded: {len(info['components'])}")
    print("="*60 + "\n")

# Export module info for external access
MODULE_INFO = get_module_info()