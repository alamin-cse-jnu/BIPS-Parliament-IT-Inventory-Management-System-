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
        if not obj.is_prp_managed:
            return format_html('<span style="color: #6c757d;">N/A</span>')
        
        if obj.prp_last_sync is None:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠️ Never Synced</span>'
            )
        
        # Calculate time since last sync (Asia/Dhaka timezone)
        now = timezone.now()
        time_diff = now - obj.prp_last_sync
        
        if time_diff.days > 7:
            color = '#dc3545'  # Red for old sync
            status = f'🕐 {time_diff.days}d ago'
        elif time_diff.days > 1:
            color = '#ffc107'  # Yellow for moderate sync
            status = f'🕐 {time_diff.days}d ago'
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            color = '#28a745'  # Green for recent sync
            status = f'🕐 {hours}h ago'
        else:
            color = '#28a745'  # Green for very recent
            status = '✅ Recent'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    get_sync_status_display.short_description = 'Last Sync'
    get_sync_status_display.admin_order_field = 'prp_last_sync'
    
    def get_prp_sync_status_display(self, obj):
        """Detailed PRP sync status for form display."""
        if not obj.is_prp_managed:
            return "This user is managed locally (not from PRP)"
        
        if obj.prp_last_sync is None:
            return "⚠️ This user has never been synced from PRP"
        
        # Format last sync time in Asia/Dhaka timezone
        local_time = obj.prp_last_sync.astimezone(timezone.get_current_timezone())
        formatted_time = local_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        
        return f"✅ Last synced: {formatted_time}"
    get_prp_sync_status_display.short_description = 'PRP Sync Status'
    
    # ========================================================================
    # EXISTING DISPLAY METHODS (PRESERVED)
    # ========================================================================
    
    def get_full_name(self, obj):
        """Display user's full name with PRP indicator."""
        full_name = obj.get_full_name() or obj.username
        if obj.is_prp_managed:
            return format_html(
                '<strong>{}</strong> <small style="color: #28a745;">[PRP]</small>',
                full_name
            )
        return full_name
    get_full_name.short_description = 'Full Name'
    
    def get_groups_display(self, obj):
        """Display user's groups/roles."""
        groups = obj.groups.all()
        if groups:
            group_links = []
            for group in groups:
                url = reverse('admin:auth_group_change', args=[group.pk])
                group_links.append(f'<a href="{url}" target="_blank">{group.name}</a>')
            return format_html(', '.join(group_links))
        return '-'
    get_groups_display.short_description = 'Groups'
    
    def get_profile_image_display(self, obj):
        """Display profile image thumbnail."""
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;" />',
                obj.profile_image.url
            )
        return '👤'
    get_profile_image_display.short_description = 'Image'
    
    # ========================================================================
    # QUERYSET OPTIMIZATION
    # ========================================================================
    
    def get_queryset(self, request):
        """Optimize queries with prefetch_related."""
        return super().get_queryset(request).prefetch_related(
            'groups'
        ).select_related()
    
    # ========================================================================
    # FORM CUSTOMIZATION FOR PRP USERS
    # ========================================================================
    
    def get_readonly_fields(self, request, obj=None):
        """Make PRP-sourced fields read-only for PRP users."""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        if obj and obj.is_prp_managed:
            # Add PRP-sourced fields to readonly for PRP users
            prp_readonly_fields = [
                'employee_id',      # PRP userId
                'first_name',       # PRP nameEng (split)
                'last_name',        # PRP nameEng (split)
                'email',            # PRP email
                'designation',      # PRP designationEng
                'office',           # PRP department nameEng
                'phone_number',     # PRP mobile
                'profile_image',    # PRP photo (converted)
                'is_prp_managed',   # PRP management flag
                'prp_last_sync'     # PRP sync timestamp
            ]
            readonly_fields.extend(prp_readonly_fields)
        
        return readonly_fields
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form for PRP users."""
        form = super().get_form(request, obj, **kwargs)
        
        if obj and obj.is_prp_managed:
            # Add help text for PRP users
            for field_name in obj.get_prp_readonly_fields():
                if field_name in form.base_fields:
                    current_help = form.base_fields[field_name].help_text
                    prp_help = "This field is managed by PRP and cannot be edited."
                    form.base_fields[field_name].help_text = f"{current_help} {prp_help}".strip()
        
        return form
    
    # ========================================================================
    # PRP ADMIN ACTIONS
    # ========================================================================
    
    actions = [
        'activate_users',
        'deactivate_users',
        'make_staff',
        'remove_staff',
        'sync_selected_prp_users',
        'bulk_sync_all_prp_users',
        'check_prp_sync_status'
    ]
    
    # Existing actions (preserved)
    def activate_users(self, request, queryset):
        """Activate selected users."""
        updated = queryset.update(is_active=True, is_active_employee=True)
        self.message_user(request, f'{updated} users were successfully activated.')
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        updated = queryset.update(is_active=False, is_active_employee=False)
        self.message_user(request, f'{updated} users were successfully deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'
    
    def make_staff(self, request, queryset):
        """Make selected users staff members."""
        updated = queryset.update(is_staff=True)
        self.message_user(request, f'{updated} users were granted staff status.')
    make_staff.short_description = 'Grant staff status'
    
    def remove_staff(self, request, queryset):
        """Remove staff status from selected users."""
        updated = queryset.filter(is_superuser=False).update(is_staff=False)
        self.message_user(request, f'{updated} users had staff status removed.')
    remove_staff.short_description = 'Remove staff status'
    
    # ========================================================================
    # NEW PRP SYNC ACTIONS
    # ========================================================================
    
    def sync_selected_prp_users(self, request, queryset):
        """Sync selected PRP users from Parliament Resource Portal."""
        if not PRP_INTEGRATION_AVAILABLE:
            self.message_user(
                request, 
                'PRP integration is not available. Please check the sync service configuration.',
                level=messages.ERROR
            )
            return
        
        # Filter for PRP-managed users only
        prp_users = queryset.filter(is_prp_managed=True)
        non_prp_count = queryset.count() - prp_users.count()
        
        if non_prp_count > 0:
            self.message_user(
                request,
                f'Skipped {non_prp_count} non-PRP users. Only PRP-managed users can be synced.',
                level=messages.WARNING
            )
        
        if not prp_users.exists():
            self.message_user(
                request,
                'No PRP-managed users selected for synchronization.',
                level=messages.WARNING
            )
            return
        
        try:
            # Initialize PRP sync service
            prp_client = create_prp_client()
            sync_service = PRPSyncService(prp_client)
            
            synced_count = 0
            error_count = 0
            
            with transaction.atomic():
                for user in prp_users:
                    try:
                        # Sync individual user by employee_id (PRP userId)
                        result = sync_service.sync_user_by_employee_id(user.employee_id)
                        if result and result.success:
                            synced_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        logger.error(f"Failed to sync user {user.employee_id}: {e}")
                        error_count += 1
            
            # Report results
            if synced_count > 0 and error_count == 0:
                self.message_user(
                    request,
                    f'Successfully synced {synced_count} PRP users from Parliament Resource Portal.',
                    level=messages.SUCCESS
                )
            elif synced_count > 0 and error_count > 0:
                self.message_user(
                    request,
                    f'Synced {synced_count} users successfully, {error_count} users had errors.',
                    level=messages.WARNING
                )
            else:
                self.message_user(
                    request,
                    f'Failed to sync users. Please check the PRP connection and try again.',
                    level=messages.ERROR
                )
                
        except (PRPConnectionError, PRPAuthenticationError) as e:
            self.message_user(
                request,
                f'PRP connection failed: {str(e)}. Please check the Parliament Resource Portal connection.',
                level=messages.ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error in PRP sync: {e}")
            self.message_user(
                request,
                f'Unexpected error during sync: {str(e)}',
                level=messages.ERROR
            )
    
    sync_selected_prp_users.short_description = '📡 Sync selected PRP users from Parliament Portal'
    
    def bulk_sync_all_prp_users(self, request, queryset):
        """Bulk sync all PRP users from all departments."""
        if not PRP_INTEGRATION_AVAILABLE:
            self.message_user(
                request, 
                'PRP integration is not available. Please check the sync service configuration.',
                level=messages.ERROR
            )
            return
        
        # Confirmation required for bulk operations
        if 'confirmed' not in request.POST:
            return render(request, 'admin/users/bulk_sync_confirmation.html', {
                'title': 'Bulk Sync All PRP Users',
                'message': 'This will sync all users from Parliament Resource Portal (PRP). This operation may take several minutes.',
                'action': 'bulk_sync_all_prp_users'
            })
        
        try:
            # Initialize PRP sync service
            prp_client = create_prp_client()
            sync_service = PRPSyncService(prp_client)
            
            # Perform bulk sync
            with transaction.atomic():
                result = sync_service.sync_all_departments()
            
            if result and result.success:
                self.message_user(
                    request,
                    f'Bulk sync completed successfully. '
                    f'Processed {result.total_processed} users, '
                    f'{result.created_count} created, '
                    f'{result.updated_count} updated, '
                    f'{result.error_count} errors.',
                    level=messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    'Bulk sync completed with errors. Please check the logs for details.',
                    level=messages.WARNING
                )
                
        except (PRPConnectionError, PRPAuthenticationError) as e:
            self.message_user(
                request,
                f'PRP connection failed: {str(e)}. Please verify Parliament Resource Portal connectivity.',
                level=messages.ERROR
            )
        except Exception as e:
            logger.error(f"Bulk sync error: {e}")
            self.message_user(
                request,
                f'Bulk sync failed: {str(e)}',
                level=messages.ERROR
            )
    
    bulk_sync_all_prp_users.short_description = '🔄 Bulk sync ALL users from Parliament Portal'
    
    def check_prp_sync_status(self, request, queryset):
        """Check PRP sync status for selected users."""
        prp_users = queryset.filter(is_prp_managed=True)
        non_prp_users = queryset.filter(is_prp_managed=False)
        
        never_synced = prp_users.filter(prp_last_sync__isnull=True).count()
        recently_synced = prp_users.filter(
            prp_last_sync__gte=timezone.now() - timedelta(hours=24)
        ).count()
        needs_sync = prp_users.filter(
            prp_last_sync__lt=timezone.now() - timedelta(days=7)
        ).count()
        
        status_message = (
            f'PRP Sync Status Report:\n'
            f'• Total selected: {queryset.count()} users\n'
            f'• PRP-managed: {prp_users.count()} users\n'
            f'• Local users: {non_prp_users.count()} users\n'
            f'• Never synced: {never_synced} users\n'
            f'• Recently synced (24h): {recently_synced} users\n'
            f'• Needs sync (>7 days): {needs_sync} users'
        )
        
        self.message_user(request, status_message)
    
    check_prp_sync_status.short_description = '📊 Check PRP sync status'
    
    # ========================================================================
    # FORM WIDGET CUSTOMIZATIONS
    # ========================================================================
    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 80})},
    }
    
    def save_model(self, request, obj, form, change):
        """Custom save logic with PRP considerations."""
        # Preserve admin modification tracking
        if not change:  # Creating new user
            if not obj.is_prp_managed:
                obj.notes = f"Created by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Prevent accidental PRP flag changes
        if change and obj.is_prp_managed and 'is_prp_managed' in form.changed_data:
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
            'total_prp_users': CustomUser.objects.filter(is_prp_managed=True).count(),
            'never_synced': CustomUser.objects.filter(
                is_prp_managed=True, 
                prp_last_sync__isnull=True
            ).count()
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


class PermissionAdminCustom(admin.ModelAdmin):
    """
    Custom admin interface for Permissions.
    Preserved from existing implementation.
    """
    list_display = ('name', 'content_type', 'codename')
    list_filter = ('content_type',)
    search_fields = ('name', 'codename', 'content_type__model')
    ordering = ('content_type', 'codename')


# ============================================================================
# ADMIN REGISTRATION
# ============================================================================

# Register enhanced CustomUser admin
admin.site.register(CustomUser, CustomUserAdmin)

# Unregister and re-register Group admin with custom version
admin.site.unregister(Group)
admin.site.register(Group, GroupAdminCustom)

# Optional: Register Permission with custom admin
# admin.site.register(Permission, PermissionAdminCustom)

# ============================================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================================

# Customize admin site headers for Bangladesh Parliament Secretariat
admin.site.site_header = 'PIMS Administration - Parliament Secretariat'
admin.site.site_title = 'PIMS Admin'
admin.site.index_title = 'Bangladesh Parliament Secretariat - IT Inventory Management System'

# Add PRP integration status to admin index
if hasattr(admin.site, 'each_context'):
    original_each_context = admin.site.each_context
    
    def enhanced_each_context(request):
        """Add PRP integration status to admin context."""
        context = original_each_context(request)
        context.update({
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'prp_users_count': CustomUser.objects.filter(is_prp_managed=True).count() if CustomUser.objects.exists() else 0,
            'local_users_count': CustomUser.objects.filter(is_prp_managed=False).count() if CustomUser.objects.exists() else 0,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        })
        return context
    
    admin.site.each_context = enhanced_each_context