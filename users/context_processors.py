"""
Context Processors for Users App
Bangladesh Parliament Secretariat IT Inventory Management System
Location: Dhaka, Bangladesh

Provides global template context for PRP integration and user-related functionality.
"""

from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def prp_integration_status(request):
    """
    Context processor for PRP (Parliament Resource Portal) integration status.
    
    Provides global template variables related to PRP integration:
    - PRP integration availability
    - PRP sync statistics
    - User source information
    - Bangladesh Parliament Secretariat location context
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Context variables for templates
    """
    context = {
        'prp_integration_available': getattr(settings, 'PRP_INTEGRATION_AVAILABLE', False),
        'prp_api_enabled': getattr(settings, 'PRP_API_ENABLED', False),
        'location': 'Bangladesh Parliament Secretariat, Dhaka',
        'timezone_display': 'Asia/Dhaka',
    }
    
    # Add PRP business rules if available
    prp_business_rules = getattr(settings, 'PRP_BUSINESS_RULES', {})
    if prp_business_rules:
        context.update({
            'prp_one_way_sync': prp_business_rules.get('ONE_WAY_SYNC_ONLY', True),
            'prp_admin_control': prp_business_rules.get('ADMIN_CONTROLLED_SYNC', True),
            'prp_default_password': prp_business_rules.get('DEFAULT_PASSWORD_FOR_PRP_USERS', False),
        })
    
    # Add template design settings if available
    template_settings = getattr(settings, 'PIMS_TEMPLATE_SETTINGS', {})
    if template_settings:
        context.update({
            'design_system': template_settings.get('DESIGN_SYSTEM', 'flat'),
            'color_scheme': template_settings.get('COLOR_SCHEME', {}),
            'high_contrast': template_settings.get('HIGH_CONTRAST', True),
            'responsive_breakpoints': template_settings.get('RESPONSIVE_BREAKPOINTS', []),
        })
    
    # Add user statistics if user is authenticated and has permissions
    if request.user.is_authenticated and request.user.has_perm('auth.view_user'):
        try:
            from users.models import CustomUser
            
            # Basic user counts
            context.update({
                'total_users_count': CustomUser.objects.count(),
                'active_users_count': CustomUser.objects.filter(is_active=True).count(),
                'staff_users_count': CustomUser.objects.filter(is_staff=True, is_active=True).count(),
            })
            
            # PRP-specific counts if PRP integration is available
            if hasattr(CustomUser, 'is_prp_managed') and context['prp_integration_available']:
                now = timezone.now()
                prp_users_count = CustomUser.objects.filter(is_prp_managed=True).count()
                local_users_count = CustomUser.objects.filter(is_prp_managed=False).count()
                
                # Sync status counts
                never_synced = CustomUser.objects.filter(
                    is_prp_managed=True,
                    prp_last_sync__isnull=True
                ).count()
                
                recently_synced = CustomUser.objects.filter(
                    is_prp_managed=True,
                    prp_last_sync__gte=now - timedelta(hours=24)
                ).count()
                
                needs_sync = CustomUser.objects.filter(
                    is_prp_managed=True,
                    prp_last_sync__lt=now - timedelta(days=7)
                ).count()
                
                context.update({
                    'prp_users_count': prp_users_count,
                    'local_users_count': local_users_count,
                    'prp_never_synced': never_synced,
                    'prp_recently_synced': recently_synced,
                    'prp_needs_sync': needs_sync,
                })
                
        except ImportError:
            # Graceful fallback if CustomUser model not available
            pass
        except Exception:
            # Graceful fallback for any database issues
            pass
    
    return context


def user_permissions_context(request):
    """
    Context processor for user permissions and role information.
    
    Provides template variables for user permissions and roles:
    - User role information
    - Permission checks
    - Admin status
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Context variables for templates
    """
    context = {
        'is_authenticated': request.user.is_authenticated,
        'is_staff': False,
        'is_superuser': False,
        'user_groups': [],
        'has_user_management_perms': False,
        'has_device_management_perms': False,
        'has_location_management_perms': False,
        'has_assignment_management_perms': False,
        'has_maintenance_management_perms': False,
        'has_vendor_management_perms': False,
    }
    
    if request.user.is_authenticated:
        context.update({
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
            'user_groups': request.user.groups.all(),
        })
        
        # Permission checks for main modules
        context.update({
            'has_user_management_perms': (
                request.user.has_perm('auth.add_user') or 
                request.user.has_perm('auth.change_user') or 
                request.user.has_perm('auth.delete_user')
            ),
            'has_device_management_perms': (
                request.user.has_perm('devices.add_device') or 
                request.user.has_perm('devices.change_device') or 
                request.user.has_perm('devices.delete_device')
            ),
            'has_location_management_perms': (
                request.user.has_perm('locations.add_location') or 
                request.user.has_perm('locations.change_location') or 
                request.user.has_perm('locations.delete_location')
            ),
            'has_assignment_management_perms': (
                request.user.has_perm('assignments.add_assignment') or 
                request.user.has_perm('assignments.change_assignment') or 
                request.user.has_perm('assignments.delete_assignment')
            ),
            'has_maintenance_management_perms': (
                request.user.has_perm('maintenance.add_maintenance') or 
                request.user.has_perm('maintenance.change_maintenance') or 
                request.user.has_perm('maintenance.delete_maintenance')
            ),
            'has_vendor_management_perms': (
                request.user.has_perm('vendors.add_vendor') or 
                request.user.has_perm('vendors.change_vendor') or 
                request.user.has_perm('vendors.delete_vendor')
            ),
        })
    
    return context


def system_info_context(request):
    """
    Context processor for system information.
    
    Provides system-wide template variables:
    - System name and version
    - Location information
    - Current date/time in local timezone
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        dict: Context variables for templates
    """
    context = {
        'system_name': 'PIMS',
        'system_full_name': 'Parliament IT Inventory Management System',
        'organization': 'Bangladesh Parliament Secretariat',
        'location_city': 'Dhaka',
        'location_country': 'Bangladesh',
        'current_year': timezone.now().year,
        'local_timezone': 'Asia/Dhaka',
    }
    
    # Add debug information if in DEBUG mode
    if getattr(settings, 'DEBUG', False):
        context.update({
            'debug_mode': True,
            'django_version': getattr(settings, 'DJANGO_VERSION', 'Unknown'),
            'python_version': getattr(settings, 'PYTHON_VERSION', 'Unknown'),
        })
    
    return context