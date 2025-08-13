"""
Django Admin configuration for Users app in PIMS
Bangladesh Parliament Secretariat

This module customizes the Django admin interface for CustomUser model
and provides enhanced user management capabilities.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import models
from django.forms import Textarea
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    """
    Custom admin interface for CustomUser model.
    Extends Django's default UserAdmin with additional fields and functionality.
    """
    
    # Display configuration
    list_display = (
        'employee_id',
        'username', 
        'get_full_name',
        'email',
        'office',
        'designation',
        'is_active_employee',
        'is_staff',
        'get_groups_display',
        'get_profile_image_display',
        'created_at'
    )
    
    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'is_active_employee',
        'office',
        'designation',
        'groups',
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
    
    # Form layout configuration
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
                'employee_id',
                'first_name',
                'last_name',
                'email',
                'password1',
                'password2'
            )
        }),
        ('Employee Details', {
            'classes': ('wide',),
            'fields': (
                'designation',
                'office',
                'phone_number',
                'is_active_employee'
            )
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': (
                'is_active',
                'is_staff',
                'groups'
            )
        })
    )
    
    # Read-only fields
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    # Filter horizontal for many-to-many fields
    filter_horizontal = ('groups', 'user_permissions')
    
    # Actions
    actions = ['activate_users', 'deactivate_users', 'make_staff', 'remove_staff']

    def get_full_name(self, obj):
        """Display full name in list view."""
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'first_name'

    def get_groups_display(self, obj):
        """Display user groups as colored badges."""
        if obj.groups.exists():
            groups = []
            for group in obj.groups.all():
                if 'admin' in group.name.lower():
                    color = '#dc3545'  # Red for admin
                elif 'staff' in group.name.lower():
                    color = '#ffc107'  # Yellow for staff
                else:
                    color = '#28a745'  # Green for regular users
                
                groups.append(f'<span style="background-color: {color}; color: white; '
                             f'padding: 2px 8px; border-radius: 12px; font-size: 11px; '
                             f'margin-right: 5px;">{group.name}</span>')
            return mark_safe(''.join(groups))
        return '-'
    get_groups_display.short_description = 'Roles'

    def get_profile_image_display(self, obj):
        """Display profile image thumbnail in list view."""
        if obj.profile_image:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius: 50%; object-fit: cover;" />',
                obj.profile_image.url
            )
        return '📷'
    get_profile_image_display.short_description = 'Photo'

    def get_queryset(self, request):
        """Optimize queryset with prefetch_related for groups."""
        return super().get_queryset(request).prefetch_related('groups')

    # Custom actions
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

    # Form widget customizations
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 80})},
    }

    def save_model(self, request, obj, form, change):
        """Custom save logic."""
        # Log who created or modified the user
        if not change:  # Creating new user
            obj.notes = f"Created by {request.user.username}"
        super().save_model(request, obj, form, change)


class GroupAdminCustom(admin.ModelAdmin):
    """
    Custom admin interface for Groups (Roles).
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
    """
    list_display = ('name', 'content_type', 'codename')
    list_filter = ('content_type',)
    search_fields = ('name', 'codename', 'content_type__model')
    ordering = ('content_type', 'codename')


# Register models with admin
admin.site.register(CustomUser, CustomUserAdmin)

# Unregister default Group admin and register custom one
admin.site.unregister(Group)
admin.site.register(Group, GroupAdminCustom)

# Register Permission with custom admin (optional)
# admin.site.register(Permission, PermissionAdminCustom)

# Customize admin site headers
admin.site.site_header = 'PIMS Administration'
admin.site.site_title = 'PIMS Admin'
admin.site.index_title = 'Bangladesh Parliament Secretariat - IT Inventory Management'