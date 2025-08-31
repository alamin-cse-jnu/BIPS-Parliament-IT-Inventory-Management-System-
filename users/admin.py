"""
Django Admin configuration for Users app in PIMS
Bangladesh Parliament Secretariat, Dhaka

Enhanced CustomUserAdmin with PRP (Parliament Resource Portal) Integration
This module extends the existing Django admin interface with PRP sync features,
maintaining backwards compatibility while adding comprehensive PRP management.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Admin-controlled synchronization and management of PRP users
"""

import logging
from datetime import datetime, timedelta
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.db import models
from django.forms import Textarea
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import CustomUser

# Import PRP integration modules (with fallback for development)
try:
    from .api.sync_service import PRPSyncService
    from .api.prp_client import create_prp_client
    from .api.exceptions import (
        PRPException,
        PRPConnectionError,
        PRPAuthenticationError,
        PRPSyncError,
        PRPDataValidationError
    )
    PRP_INTEGRATION_AVAILABLE = True
except ImportError:
    PRP_INTEGRATION_AVAILABLE = False
    PRPException = Exception  # Fallback

# Configure logging
logger = logging.getLogger('pims.admin.prp_sync')


class CustomUserAdmin(UserAdmin):
    """
    Enhanced CustomUser admin interface with PRP (Parliament Resource Portal) integration.
    
    Extends Django's default UserAdmin with:
    - PRP sync management features
    - Bulk sync operations
    - PRP status display and filtering
    - Read-only PRP fields protection
    - Comprehensive sync history tracking
    """
    
    # ========================================================================
    # DISPLAY CONFIGURATION
    # ========================================================================
    
    list_display = (
        'employee_id',
        'username', 
        'get_full_name',
        'email',
        'office',
        'designation',
        'get_prp_status_display',
        'get_sync_status_display',
        'is_active_employee',
        'is_staff',
        'get_groups_display',
        'get_profile_image_display',
        'created_at'
    )
    
    list_filter = (
        'is_prp_managed',  # PRP filter first for easy identification
        'is_active',
        'is_staff',
        'is_superuser',
        'is_active_employee',
        'office',
        'designation',
        'groups',
        'prp_last_sync',
        'created_at',
        'last_login'
    )
    
    search_fields = (
        'username',
        'first_name',
        'last_name',
        'employee_id',
        'email',
        'office',
        'designation',
        'phone_number'
    )
    
    ordering = ('employee_id', 'username')
    
    # ========================================================================
    # FORM LAYOUT CONFIGURATION WITH PRP FIELDS
    # ========================================================================
    
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'password')
        }),
        ('Personal Information', {
            'fields': (
                'first_name',
                'last_name', 
                'email',
                'profile_image'
            )
        }),
        ('Employee Information', {
            'fields': (
                'employee_id',
                'designation',
                'office',
                'phone_number'
            )
        }),
        ('PRP Integration', {
            'fields': (
                'is_prp_managed',
                'prp_last_sync',
                'get_prp_sync_status_display'
            ),
            'classes': ('collapse',),
            'description': 'PRP (Parliament Resource Portal) synchronization status and management.'
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_active_employee',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    # Add user form configuration
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': (
                'username',
                'password1',
                'password2',
                'employee_id',
                'first_name',
                'last_name',
                'email'
            )
        }),
        ('Employee Information', {
            'classes': ('wide',),
            'fields': (
                'designation',
                'office',
                'phone_number',
                'is_active',
                'is_active_employee'
            )
        })
    )
    
    # Read-only fields (includes PRP sync status)
    readonly_fields = (
        'created_at',
        'updated_at',
        'last_login',
        'get_prp_sync_status_display'
    )
    
    # ========================================================================
    # PRP DISPLAY METHODS
    # ========================================================================
    
    def get_prp_status_display(self, obj):
        """Display PRP management status with visual indicators."""
        if not hasattr(obj, 'is_prp_managed'):
            return format_html('<span style="color: #6c757d;">🏢 Local User</span>')
            
        if obj.is_prp_managed:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">📡 PRP Managed</span>'
            )
        return format_html(
            '<span style="color: #6c757d;">🏢 Local User</span>'
        )
    get_prp_status_display.short_description = 'User Source'
    get_prp_status_display.admin_order_field = 'is_prp_managed'
    
    def get_sync_status_display(self, obj):
        """Display PRP sync status with timestamp information."""
        if not hasattr(obj, 'is_prp_managed') or not obj.is_prp_managed:
            return format_html('<span style="color: #6c757d;">N/A (Local User)</span>')
            
        if not hasattr(obj, 'prp_last_sync') or not obj.prp_last_sync:
            return format_html('<span style="color: #dc3545;">⚠️ Never Synced</span>')
            
        # Convert to Dhaka timezone for display
        dhaka_time = obj.prp_last_sync.astimezone(timezone.get_current_timezone())
        time_ago = timezone.now() - obj.prp_last_sync
        
        if time_ago.days > 30:
            status_color = '#dc3545'  # Red for old sync
            status_icon = '🔴'
        elif time_ago.days > 7:
            status_color = '#ffc107'  # Yellow for week-old sync
            status_icon = '🟡'
        else:
            status_color = '#28a745'  # Green for recent sync
            status_icon = '🟢'
            
        return format_html(
            '<span style="color: {};">{} {}</span>',
            status_color,
            status_icon,
            dhaka_time.strftime('%Y-%m-%d %H:%M:%S')
        )
    get_sync_status_display.short_description = 'Last PRP Sync'
    get_sync_status_display.admin_order_field = 'prp_last_sync'
    
    def get_prp_sync_status_display(self, obj):
        """Detailed PRP sync status for form view."""
        if not hasattr(obj, 'is_prp_managed') or not obj.is_prp_managed:
            return format_html(
                '<div style="background: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 4px solid #6c757d;">'
                '<strong>Local PIMS User</strong><br>'
                'This user was created directly in PIMS and is not managed by PRP.'
                '</div>'
            )
            
        if not hasattr(obj, 'prp_last_sync') or not obj.prp_last_sync:
            return format_html(
                '<div style="background: #fff3cd; padding: 12px; border-radius: 8px; border-left: 4px solid #ffc107;">'
                '<strong>⚠️ PRP User - Never Synced</strong><br>'
                'This user is managed by PRP but has never been synchronized.<br>'
                '<em>Consider running a manual sync operation.</em>'
                '</div>'
            )
        
        # Convert to Dhaka timezone
        dhaka_time = obj.prp_last_sync.astimezone(timezone.get_current_timezone())
        time_ago = timezone.now() - obj.prp_last_sync
        
        if time_ago.days > 30:
            bg_color = '#f8d7da'
            border_color = '#dc3545'
            status_text = f'🔴 Last synced {time_ago.days} days ago'
            recommendation = 'Consider running a fresh sync to ensure data accuracy.'
        elif time_ago.days > 7:
            bg_color = '#fff3cd'
            border_color = '#ffc107'
            status_text = f'🟡 Last synced {time_ago.days} days ago'
            recommendation = 'Sync is moderately outdated.'
        else:
            bg_color = '#d4edda'
            border_color = '#28a745'
            status_text = '🟢 Recently synced'
            recommendation = 'Sync status is current.'
            
        return format_html(
            '<div style="background: {}; padding: 12px; border-radius: 8px; border-left: 4px solid {};">'
            '<strong>📡 PRP Managed User</strong><br>'
            '{}<br>'
            'Last sync: {}<br>'
            '<em>{}</em>'
            '</div>',
            bg_color, border_color, status_text, 
            dhaka_time.strftime('%Y-%m-%d %H:%M:%S (%Z)'), 
            recommendation
        )
    get_prp_sync_status_display.short_description = 'PRP Sync Status'
    
    def get_full_name(self, obj):
        """Display user's full name with PRP indicator."""
        full_name = obj.get_full_name() or obj.username
        if hasattr(obj, 'is_prp_managed') and obj.is_prp_managed:
            return format_html(
                '{} <span style="background: #14b8a6; color: white; padding: 2px 6px; '
                'border-radius: 4px; font-size: 0.75em;">PRP</span>',
                full_name
            )
        return full_name
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'first_name'
    
    def get_groups_display(self, obj):
        """Display user groups with count."""
        groups = obj.groups.all()
        if not groups:
            return format_html('<span style="color: #6c757d;">No roles</span>')
        
        group_list = ', '.join([group.name for group in groups[:3]])
        if len(groups) > 3:
            group_list += f' (+{len(groups) - 3} more)'
        
        return format_html('<span title="{}">{}</span>', group_list, group_list)
    get_groups_display.short_description = 'Roles'
    
    def get_profile_image_display(self, obj):
        """Display profile image thumbnail."""
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; '
                'object-fit: cover;" alt="Profile">',
                obj.profile_image.url
            )
        return format_html('<span style="color: #6c757d;">No image</span>')
    get_profile_image_display.short_description = 'Photo'
    
    # ========================================================================
    # ADMIN ACTIONS FOR PRP SYNC
    # ========================================================================
    
    actions = ['sync_selected_from_prp', 'force_sync_selected_from_prp', 'mark_as_prp_managed']
    
    def sync_selected_from_prp(self, request, queryset):
        """Bulk sync selected users from PRP."""
        if not PRP_INTEGRATION_AVAILABLE:
            self.message_user(
                request,
                'PRP integration is not available. Please ensure sync_service.py is implemented.',
                level=messages.ERROR
            )
            return
            
        prp_users = queryset.filter(is_prp_managed=True)
        if not prp_users.exists():
            self.message_user(
                request,
                'No PRP-managed users selected. Only PRP-managed users can be synced.',
                level=messages.WARNING
            )
            return
        
        try:
            prp_client = create_prp_client()
            sync_service = PRPSyncService(prp_client)
            
            success_count = 0
            error_count = 0
            
            with transaction.atomic():
                for user in prp_users:
                    try:
                        result = sync_service.sync_user_by_employee_id(user.employee_id)
                        if result.success:
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Failed to sync user {user.employee_id}: {e}")
            
            if success_count:
                self.message_user(
                    request,
                    f'Successfully synced {success_count} user(s) from PRP.',
                    level=messages.SUCCESS
                )
            if error_count:
                self.message_user(
                    request,
                    f'Failed to sync {error_count} user(s). Check logs for details.',
                    level=messages.WARNING
                )
                
        except Exception as e:
            self.message_user(
                request,
                f'PRP sync operation failed: {str(e)}',
                level=messages.ERROR
            )
            logger.error(f"Bulk PRP sync failed: {e}")
    
    sync_selected_from_prp.short_description = "🔄 Sync selected users from PRP"
    
    def force_sync_selected_from_prp(self, request, queryset):
        """Force sync selected users from PRP (ignores recent sync timestamps)."""
        if not PRP_INTEGRATION_AVAILABLE:
            self.message_user(
                request,
                'PRP integration is not available.',
                level=messages.ERROR
            )
            return
            
        prp_users = queryset.filter(is_prp_managed=True)
        if not prp_users.exists():
            self.message_user(
                request,
                'No PRP-managed users selected.',
                level=messages.WARNING
            )
            return
        
        try:
            prp_client = create_prp_client()
            sync_service = PRPSyncService(prp_client)
            
            success_count = 0
            error_count = 0
            
            with transaction.atomic():
                for user in prp_users:
                    try:
                        result = sync_service.sync_user_by_employee_id(
                            user.employee_id,
                            force_refresh=True
                        )
                        if result.success:
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Failed to force sync user {user.employee_id}: {e}")
            
            if success_count:
                self.message_user(
                    request,
                    f'Force synced {success_count} user(s) from PRP.',
                    level=messages.SUCCESS
                )
            if error_count:
                self.message_user(
                    request,
                    f'Failed to force sync {error_count} user(s).',
                    level=messages.WARNING
                )
                
        except Exception as e:
            self.message_user(
                request,
                f'PRP force sync failed: {str(e)}',
                level=messages.ERROR
            )
    
    force_sync_selected_from_prp.short_description = "🔄 Force sync from PRP (ignore cache)"
    
    def mark_as_prp_managed(self, request, queryset):
        """Mark selected users as PRP-managed (admin override)."""
        if not hasattr(CustomUser, 'is_prp_managed'):
            self.message_user(
                request,
                'PRP management fields are not available in the user model.',
                level=messages.ERROR
            )
            return
        
        updated = queryset.update(is_prp_managed=True)
        self.message_user(
            request,
            f'Marked {updated} user(s) as PRP-managed. '
            'These users will now be subject to PRP sync operations.',
            level=messages.SUCCESS
        )
    
    mark_as_prp_managed.short_description = "📡 Mark as PRP-managed"
    
    # ========================================================================
    # FORM CUSTOMIZATION FOR PRP
    # ========================================================================
    
    def get_readonly_fields(self, request, obj=None):
        """Make PRP-sourced fields read-only."""
        readonly = list(self.readonly_fields)
        
        if obj and hasattr(obj, 'is_prp_managed') and obj.is_prp_managed:
            # Make PRP-sourced fields read-only
            readonly.extend([
                'employee_id',
                'first_name',
                'last_name',
                'email',
                'designation',
                'office',
                'phone_number',
                'profile_image',
                'is_prp_managed',
                'prp_last_sync'
            ])
        
        return readonly
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form for PRP users."""
        form = super().get_form(request, obj, **kwargs)
        
        if obj and hasattr(obj, 'is_prp_managed') and obj.is_prp_managed:
            # Add help text for PRP-managed users
            form.base_fields['employee_id'].help_text = (
                'Employee ID from PRP. This field cannot be modified as it is synced from PRP.'
            )
            form.base_fields['email'].help_text = (
                'Email from PRP. This field is automatically synced and cannot be modified.'
            )
            if 'first_name' in form.base_fields:
                form.base_fields['first_name'].help_text = (
                    'Name from PRP. This field is automatically synced.'
                )
        
        return form
    
    # ========================================================================
    # SAVE OPERATIONS WITH PRP LOGIC
    # ========================================================================
    
    def save_model(self, request, obj, form, change):
        """Enhanced save with PRP integration logic."""
        # Set default timezone for timestamps
        if not change:  # Creating new user
            obj.created_at = timezone.now()
        
        # Prevent manual editing of PRP-managed user core fields
        if change and hasattr(obj, 'is_prp_managed') and obj.is_prp_managed:
            protected_fields = [
                'employee_id', 'first_name', 'last_name', 'email',
                'designation', 'office', 'phone_number'
            ]
            
            for field in protected_fields:
                if field in form.changed_data:
                    messages.warning(
                        request,
                        f'Warning: {field.replace("_", " ").title()} is managed by PRP. '
                        'Changes may be overwritten during the next sync.'
                    )
        
        # Preserve admin modification tracking
        if not change:  # Creating new user
            if not hasattr(obj, 'is_prp_managed') or not obj.is_prp_managed:
                obj.notes = f"Created by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Prevent accidental PRP flag changes
        if change and hasattr(obj, 'is_prp_managed') and obj.is_prp_managed and 'is_prp_managed' in form.changed_data:
            messages.warning(
                request,
                'Warning: Changing PRP management status can affect sync behavior. '
                'Ensure this change is intentional.'
            )
        
        super().save_model(request, obj, form, change)
    
    # ========================================================================
    # CUSTOM ADMIN URLS (Optional - for future PRP management views)
    # ========================================================================
    
    def get_urls(self):
        """Add custom admin URLs for PRP management."""
        urls = super().get_urls()
        custom_urls = [
            path(
                'prp-sync-dashboard/',
                self.admin_site.admin_view(self.prp_sync_dashboard_view),
                name='users_customuser_prp_sync_dashboard'
            ),
        ]
        return custom_urls + urls
    
    def prp_sync_dashboard_view(self, request):
        """Custom view for PRP sync dashboard (placeholder for future development)."""
        # This is a placeholder for a future comprehensive PRP sync dashboard
        context = {
            'title': 'PRP Sync Dashboard',
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'total_prp_users': CustomUser.objects.filter(is_prp_managed=True).count() if hasattr(CustomUser, 'is_prp_managed') else 0,
            'never_synced': CustomUser.objects.filter(
                is_prp_managed=True, 
                prp_last_sync__isnull=True
            ).count() if hasattr(CustomUser, 'is_prp_managed') else 0
        }
        
        return render(request, 'admin/users/prp_sync_dashboard.html', context)


# ============================================================================
# GROUP ADMIN (PRESERVED FROM EXISTING)
# ============================================================================

class GroupAdminCustom(admin.ModelAdmin):
    """
    Custom admin interface for Groups (Roles).
    Preserved from existing implementation.
    """
    list_display = ('name', 'get_permissions_count', 'get_users_count')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    
    def get_permissions_count(self, obj):
        """Display number of permissions in the group."""
        count = obj.permissions.count()
        return f"{count} permission{'s' if count != 1 else ''}"
    get_permissions_count.short_description = 'Permissions'
    
    def get_users_count(self, obj):
        """Display number of users in the group."""
        count = obj.user_set.count()
        return f"{count} user{'s' if count != 1 else ''}"
    get_users_count.short_description = 'Users'


# ============================================================================
# ADMIN REGISTRATION
# ============================================================================

# Unregister default User and Group admin if they exist
admin.site.unregister(Group)

# Register enhanced admin interfaces
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Group, GroupAdminCustom)

# ============================================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================================

admin.site.site_header = "PIMS Administration - Bangladesh Parliament Secretariat"
admin.site.site_title = "PIMS Admin - Parliament IT Management"
admin.site.index_title = "Parliament IT Inventory Management System"

# Add custom CSS for admin interface
admin.site.site_url = None  # Remove "View site" link

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Ensure PRP admin operations are logged
def log_prp_admin_action(action, user_id, admin_user, details=""):
    """Log PRP admin actions for audit trail."""
    logger.info(
        f"PRP Admin Action: {action} | User ID: {user_id} | "
        f"Admin: {admin_user} | Details: {details} | "
        f"Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )