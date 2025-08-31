"""
users/views.py
==============
PIMS User Management Views with PRP Integration
Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh

Purpose: Remove all mock data functionality and implement real PRP API integration
Integration: PRP (Parliament Resource Portal) → PIMS (One-way sync)
Business Rules: NO user creation from PIMS, PRP fields read-only, admin-controlled sync

PRP Data Mapping:
- userId → employee_id  
- nameEng → first_name + last_name (split)
- email → email
- designationEng → designation  
- mobile → phone_number
- photo → profile_image (converted)
- status → is_active + is_active_employee
- department.nameEng → office

Dependencies: sync_service.py, prp_client.py, exceptions.py (already implemented)
"""

import csv
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, IntegrityError
from django.db.models import Q, Count, Case, When, IntegerField
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, 
    TemplateView, FormView
)

from .models import CustomUser
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm as CustomUserUpdateForm, UserRoleForm,
    CustomLoginForm, CustomPasswordResetForm, PRPSyncForm
)

# PRP Integration imports
from .api.prp_client import PRPClient
from .api.sync_service import PRPSyncService
from .api.exceptions import PRPConnectionError, PRPSyncError, PRPAuthenticationError

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# AUTHENTICATION VIEWS (Supports both PIMS local and PRP users)
# ============================================================================

class CustomLoginView(LoginView):
    """
    Custom login view supporting both PIMS local users and PRP users.
    PRP users can login with their PRP User ID as username with default password "12345678"
    """
    form_class = CustomLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Login - PIMS',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'supports_prp_login': True,  # Indicates PRP User ID login support
        })
        return context
    
    def form_valid(self, form):
        """Enhanced form validation for PRP users"""
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        
        # Authenticate user (supports both local PIMS and PRP users)
        user = authenticate(self.request, username=username, password=password)
        
        if user is not None:
            login(self.request, user)
            
            # Log successful login with PRP status
            if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
                logger.info(f"PRP user {username} logged in successfully from {self.request.META.get('REMOTE_ADDR')}")
                messages.success(self.request, f'Welcome back! (PRP User: {user.employee_id})')
            else:
                logger.info(f"Local PIMS user {username} logged in successfully from {self.request.META.get('REMOTE_ADDR')}")
                messages.success(self.request, 'Welcome back to PIMS!')
            
            return super().form_valid(form)
        else:
            # Check if this might be a new PRP user that needs to be synced
            if self._is_potential_prp_user(username):
                messages.warning(
                    self.request, 
                    'User not found in PIMS. Contact admin to sync your PRP account.'
                )
            else:
                messages.error(self.request, 'Invalid username or password.')
            
            return self.form_invalid(form)
    
    def _is_potential_prp_user(self, username: str) -> bool:
        """Check if username pattern suggests a PRP user"""
        # PRP users might login with employee ID directly
        # Pattern matching for PRP user IDs (adjust based on PRP ID format)
        return (username.isdigit() and len(username) >= 4) or username.startswith('prp_')


class CustomPasswordResetView(PasswordResetView):
    """
    Custom password reset view with PRP user awareness
    Note: PRP users cannot reset passwords (they use default "12345678")
    """
    form_class = CustomPasswordResetForm
    template_name = 'users/password_reset.html'
    success_url = reverse_lazy('users:password_reset_done')
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        
        # Check if this is a PRP-managed user
        try:
            user = CustomUser.objects.get(email=email)
            if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
                messages.warning(
                    self.request,
                    'PRP users cannot reset passwords. Please use your default PRP password or contact admin.'
                )
                return redirect('users:login')
        except CustomUser.DoesNotExist:
            pass
        
        return super().form_valid(form)

# ============================================================================
# USER MANAGEMENT VIEWS (Core PIMS functionality - preserved)
# ============================================================================

@method_decorator(login_required, name='dispatch')
class UserListView(ListView):
    """
    User list view with PRP integration support.
    Shows both local PIMS users and PRP-synced users with appropriate indicators.
    """
    model = CustomUser
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CustomUser.objects.select_related().order_by('-created_at')
        
        # Apply search filter
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(employee_id__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(office__icontains=search_query) |
                Q(designation__icontains=search_query)
            )
        
        # Apply status filter
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status_filter == 'prp':
            # Show only PRP-managed users
            if hasattr(CustomUser, 'is_prp_managed'):
                queryset = queryset.filter(is_prp_managed=True)
        elif status_filter == 'local':
            # Show only local PIMS users
            if hasattr(CustomUser, 'is_prp_managed'):
                queryset = queryset.filter(is_prp_managed=False)
        
        # Apply office filter
        office_filter = self.request.GET.get('office', '')
        if office_filter:
            queryset = queryset.filter(office__icontains=office_filter)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # User statistics with PRP breakdown
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        
        # PRP-specific statistics (if fields exist)
        prp_users = 0
        local_users = total_users
        prp_last_sync = None
        
        if hasattr(CustomUser, 'is_prp_managed'):
            prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
            local_users = total_users - prp_users
            
            # Get latest PRP sync timestamp
            latest_prp_user = CustomUser.objects.filter(
                is_prp_managed=True, 
                prp_last_sync__isnull=False
            ).order_by('-prp_last_sync').first()
            
            if latest_prp_user:
                prp_last_sync = latest_prp_user.prp_last_sync
        
        context.update({
            'page_title': 'User Management - PIMS',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'search_query': self.request.GET.get('search', ''),
            'status_filter': self.request.GET.get('status', ''),
            'office_filter': self.request.GET.get('office', ''),
            
            # Statistics
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'prp_users': prp_users,
            'local_users': local_users,
            'prp_last_sync': prp_last_sync,
            
            # Unique offices for filter dropdown
            'offices': CustomUser.objects.values_list('office', flat=True).distinct().order_by('office'),
            
            # Feature flags
            'prp_integration_enabled': True,
            'show_prp_indicators': True,
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class UserDetailView(DetailView):
    """
    User detail view with PRP integration support.
    Shows comprehensive user information including PRP sync status.
    """
    model = CustomUser
    template_name = 'users/user_detail.html'
    context_object_name = 'user_obj'  # Avoid conflict with request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        
        # PRP-specific context
        prp_context = {
            'is_prp_managed': getattr(user_obj, 'is_prp_managed', False),
            'prp_last_sync': getattr(user_obj, 'prp_last_sync', None),
            'prp_sync_status': self._get_prp_sync_status(user_obj),
            'can_sync_prp': self.request.user.is_staff,  # Only staff can trigger sync
        }
        
        context.update({
            'page_title': f'User Details: {user_obj.get_full_name()}',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            **prp_context,
        })
        
        return context
    
    def _get_prp_sync_status(self, user_obj) -> Dict[str, Any]:
        """Get PRP sync status information"""
        if not getattr(user_obj, 'is_prp_managed', False):
            return {'status': 'local', 'message': 'Local PIMS user'}
        
        last_sync = getattr(user_obj, 'prp_last_sync', None)
        if not last_sync:
            return {'status': 'never_synced', 'message': 'Never synced from PRP'}
        
        # Check sync freshness
        sync_age = timezone.now() - last_sync
        if sync_age.days > 30:
            return {
                'status': 'outdated', 
                'message': f'Last synced {sync_age.days} days ago',
                'needs_sync': True
            }
        elif sync_age.days > 7:
            return {
                'status': 'stale', 
                'message': f'Last synced {sync_age.days} days ago'
            }
        else:
            return {
                'status': 'fresh', 
                'message': f'Synced {sync_age.days} days ago'
            }


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserCreateView(CreateView):
    """
    User creation view with PRP integration constraints.
    Business Rule: NO user creation from PIMS for PRP users - they must be synced.
    """
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'users/user_create.html'
    success_url = reverse_lazy('users:list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Create User - PIMS',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'prp_integration_notice': (
                'Note: This form is for local PIMS users only. '
                'PRP users are automatically synced from the Parliament Resource Portal.'
            ),
        })
        return context
    
    def form_valid(self, form):
        """Enhanced form validation to prevent PRP user creation"""
        employee_id = form.cleaned_data.get('employee_id')
        
        # Check if this employee_id might belong to a PRP user
        if self._is_potential_prp_employee_id(employee_id):
            form.add_error(
                'employee_id',
                'This Employee ID format suggests a PRP user. '
                'Please use PRP sync instead of manual creation.'
            )
            return self.form_invalid(form)
        
        # Set as local PIMS user
        user = form.save(commit=False)
        if hasattr(user, 'is_prp_managed'):
            user.is_prp_managed = False
        user.save()
        
        messages.success(
            self.request, 
            f'Local PIMS user "{user.get_full_name()}" created successfully.'
        )
        
        logger.info(f'Local PIMS user {user.employee_id} created by {self.request.user.username}')
        return super().form_valid(form)
    
    def _is_potential_prp_employee_id(self, employee_id: str) -> bool:
        """Check if employee ID pattern suggests PRP origin"""
        # Implement pattern matching based on PRP employee ID format
        # This is a placeholder - adjust based on actual PRP ID patterns
        return employee_id.startswith('prp_') or (employee_id.isdigit() and len(employee_id) >= 6)


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserUpdateView(UpdateView):
    """
    User update view with PRP field protection.
    Business Rule: PRP-sourced fields are read-only in PIMS interface.
    """
    model = CustomUser
    form_class = CustomUserUpdateForm
    template_name = 'users/user_edit.html'
    
    def get_success_url(self):
        return reverse('users:detail', kwargs={'pk': self.object.pk})
    
    def get_form(self, form_class=None):
        """Customize form based on PRP status"""
        form = super().get_form(form_class)
        
        # If this is a PRP-managed user, make certain fields read-only
        if getattr(self.object, 'is_prp_managed', False):
            prp_readonly_fields = [
                'employee_id', 'first_name', 'last_name', 'email', 
                'designation', 'office', 'phone_number'
            ]
            
            for field_name in prp_readonly_fields:
                if field_name in form.fields:
                    form.fields[field_name].widget.attrs['readonly'] = True
                    form.fields[field_name].help_text = (
                        form.fields[field_name].help_text or ''
                    ) + ' (Read-only: Synced from PRP)'
        
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        
        context.update({
            'page_title': f'Edit User: {user_obj.get_full_name()}',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'is_prp_managed': getattr(user_obj, 'is_prp_managed', False),
            'prp_readonly_notice': (
                'Fields marked as read-only are synced from PRP and cannot be edited in PIMS.'
                if getattr(user_obj, 'is_prp_managed', False) else None
            ),
        })
        
        return context
    
    def form_valid(self, form):
        """Enhanced form validation for PRP users"""
        user_obj = self.get_object()
        
        # For PRP users, prevent modification of protected fields
        if getattr(user_obj, 'is_prp_managed', False):
            protected_fields = [
                'employee_id', 'first_name', 'last_name', 'email',
                'designation', 'office', 'phone_number'
            ]
            
            for field in protected_fields:
                if field in form.changed_data:
                    messages.error(
                        self.request,
                        f'Cannot modify {field} for PRP-managed users. Use PRP sync instead.'
                    )
                    return self.form_invalid(form)
        
        messages.success(
            self.request,
            f'User "{user_obj.get_full_name()}" updated successfully.'
        )
        
        logger.info(
            f'User {user_obj.employee_id} updated by {self.request.user.username}. '
            f'Changed fields: {form.changed_data}'
        )
        
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserDeleteView(DeleteView):
    """
    User deletion view with PRP protection.
    Business Rule: Consider implications of deleting PRP users.
    """
    model = CustomUser
    template_name = 'users/users_delete.html'
    success_url = reverse_lazy('users:list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        
        context.update({
            'page_title': f'Delete User: {user_obj.get_full_name()}',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'is_prp_managed': getattr(user_obj, 'is_prp_managed', False),
            'deletion_warning': (
                'Warning: This is a PRP-managed user. Deleting will remove local PIMS access, '
                'but the user still exists in PRP and may be re-synced.'
                if getattr(user_obj, 'is_prp_managed', False) else
                'This will permanently delete the local PIMS user account.'
            ),
        })
        
        return context
    
    def delete(self, request, *args, **kwargs):
        """Enhanced deletion with PRP awareness"""
        user_obj = self.get_object()
        username = user_obj.get_full_name()
        employee_id = user_obj.employee_id
        is_prp = getattr(user_obj, 'is_prp_managed', False)
        
        # Log deletion attempt
        logger.warning(
            f'User deletion requested: {employee_id} by {request.user.username}. '
            f'PRP managed: {is_prp}'
        )
        
        result = super().delete(request, *args, **kwargs)
        
        if is_prp:
            messages.warning(
                request,
                f'PRP user "{username}" deleted from PIMS. '
                'User may reappear on next PRP sync if still active in PRP.'
            )
        else:
            messages.success(
                request,
                f'Local PIMS user "{username}" deleted successfully.'
            )
        
        return result

# ============================================================================
# PRP INTEGRATION VIEWS (Admin-only, secured)
# ============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class PRPSyncDashboardView(TemplateView):
    """
    PRP sync dashboard for admin users.
    Provides overview of sync status, manual sync triggers, and health checks.
    """
    template_name = 'users/prp_sync_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get PRP sync statistics
        prp_stats = self._get_prp_statistics()
        prp_health = self._check_prp_health()
        recent_syncs = self._get_recent_sync_history()
        
        context.update({
            'page_title': 'PRP Integration Dashboard',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'prp_stats': prp_stats,
            'prp_health': prp_health,
            'recent_syncs': recent_syncs,
            'can_trigger_sync': True,  # Admin permission check
        })
        
        return context
    
    def _get_prp_statistics(self) -> Dict[str, Any]:
        """Get comprehensive PRP sync statistics"""
        stats = {
            'total_prp_users': 0,
            'active_prp_users': 0,
            'inactive_prp_users': 0,
            'never_synced': 0,
            'recently_synced': 0,
            'outdated_syncs': 0,
        }
        
        if hasattr(CustomUser, 'is_prp_managed'):
            prp_users = CustomUser.objects.filter(is_prp_managed=True)
            stats['total_prp_users'] = prp_users.count()
            stats['active_prp_users'] = prp_users.filter(is_active=True).count()
            stats['inactive_prp_users'] = stats['total_prp_users'] - stats['active_prp_users']
            
            # Sync freshness analysis
            now = timezone.now()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            stats['never_synced'] = prp_users.filter(prp_last_sync__isnull=True).count()
            stats['recently_synced'] = prp_users.filter(prp_last_sync__gte=week_ago).count()
            stats['outdated_syncs'] = prp_users.filter(prp_last_sync__lt=month_ago).count()
        
        return stats
    
    def _check_prp_health(self) -> Dict[str, Any]:
        """Check PRP API health status"""
        try:
            prp_client = PRPClient()
            health_status = prp_client.health_check()
            return {
                'status': 'healthy',
                'message': 'PRP API connection successful',
                'response_time': health_status.get('response_time', 'N/A'),
                'last_checked': timezone.now(),
            }
        except PRPConnectionError as e:
            return {
                'status': 'error',
                'message': f'PRP API connection failed: {str(e)}',
                'last_checked': timezone.now(),
            }
        except Exception as e:
            logger.error(f'PRP health check failed: {str(e)}')
            return {
                'status': 'error',
                'message': 'Unexpected error during health check',
                'last_checked': timezone.now(),
            }
    
    def _get_recent_sync_history(self) -> List[Dict[str, Any]]:
        """Get recent sync operation history"""
        # This would typically come from a sync log table
        # For now, return recent user sync timestamps
        recent_syncs = []
        
        if hasattr(CustomUser, 'prp_last_sync'):
            recent_users = CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__isnull=False
            ).order_by('-prp_last_sync')[:10]
            
            for user in recent_users:
                recent_syncs.append({
                    'user': user.get_full_name(),
                    'employee_id': user.employee_id,
                    'sync_time': user.prp_last_sync,
                    'status': 'success',  # Assuming successful if timestamp exists
                })
        
        return recent_syncs


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class PRPSyncTriggerView(FormView):
    """
    Manual PRP sync trigger view for admin users.
    Allows selective sync of departments or full sync.
    """
    form_class = PRPSyncForm
    template_name = 'users/prp_sync_trigger.html'
    success_url = reverse_lazy('users:prp_sync_dashboard')
    
    def form_valid(self, form):
        """Process sync request"""
        sync_type = form.cleaned_data['sync_type']
        department_id = form.cleaned_data.get('department_id')
        
        try:
            # Initialize PRP sync service
            sync_service = PRPSyncService()
            
            if sync_type == 'full':
                # Full sync of all departments
                result = sync_service.sync_all_departments()
                messages.success(
                    self.request,
                    f'Full PRP sync completed. {result["synced_users"]} users processed.'
                )
            elif sync_type == 'department' and department_id:
                # Sync specific department
                result = sync_service.sync_department_users(department_id)
                messages.success(
                    self.request,
                    f'Department sync completed. {result["synced_users"]} users processed.'
                )
            else:
                messages.error(self.request, 'Invalid sync configuration.')
                return self.form_invalid(form)
            
            # Log sync operation
            logger.info(
                f'PRP sync triggered by {self.request.user.username}. '
                f'Type: {sync_type}, Department: {department_id or "All"}'
            )
            
        except PRPConnectionError as e:
            messages.error(self.request, f'PRP connection failed: {str(e)}')
        except PRPSyncError as e:
            messages.error(self.request, f'Sync failed: {str(e)}')
        except Exception as e:
            logger.error(f'Unexpected sync error: {str(e)}')
            messages.error(self.request, 'Unexpected error during sync operation.')
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get available departments from PRP
        departments = self._get_prp_departments()
        
        context.update({
            'page_title': 'Trigger PRP Sync',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'available_departments': departments,
        })
        
        return context
    
    def _get_prp_departments(self) -> List[Dict[str, Any]]:
        """Get list of departments from PRP API"""
        try:
            prp_client = PRPClient()
            departments = prp_client.get_departments()
            return departments
        except Exception as e:
            logger.error(f'Failed to fetch PRP departments: {str(e)}')
            return []

# ============================================================================
# USER ROLE AND PERMISSION MANAGEMENT
# ============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserRoleUpdateView(UpdateView):
    """Update user roles and permissions"""
    model = CustomUser
    form_class = UserRoleForm
    template_name = 'users/user_roles.html'
    
    def get_success_url(self):
        return reverse('users:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        
        context.update({
            'page_title': f'Manage Roles: {user_obj.get_full_name()}',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'user_obj': user_obj,
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class UserPermissionView(DetailView):
    """View user permissions and group memberships"""
    model = CustomUser
    template_name = 'users/user_permissions.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        
        # Get user's groups and permissions
        user_groups = user_obj.groups.all()
        user_permissions = user_obj.user_permissions.all()
        all_permissions = user_obj.get_all_permissions()
        
        context.update({
            'page_title': f'Permissions: {user_obj.get_full_name()}',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'user_groups': user_groups,
            'user_permissions': user_permissions,
            'all_permissions': all_permissions,
        })
        
        return context

# ============================================================================
# USER STATUS MANAGEMENT (with PRP business rules)
# ============================================================================

@require_POST
@login_required
@staff_member_required
def user_activate_view(request, pk):
    """
    Activate user with PRP business rule consideration.
    For PRP users: Check if PRP status allows activation.
    """
    user_obj = get_object_or_404(CustomUser, pk=pk)
    
    try:
        # For PRP users, verify current PRP status before activation
        if getattr(user_obj, 'is_prp_managed', False):
            sync_service = PRPSyncService()
            prp_status = sync_service.get_user_prp_status(user_obj.employee_id)
            
            if prp_status and prp_status.get('status') != 'active':
                messages.warning(
                    request,
                    f'User is inactive in PRP. Please sync from PRP or activate in PRP first.'
                )
                return redirect('users:detail', pk=pk)
        
        user_obj.is_active = True
        user_obj.save()
        
        messages.success(
            request,
            f'User "{user_obj.get_full_name()}" activated successfully.'
        )
        
        logger.info(f'User {user_obj.employee_id} activated by {request.user.username}')
        
    except Exception as e:
        logger.error(f'User activation failed: {str(e)}')
        messages.error(request, 'Failed to activate user. Please try again.')
    
    return redirect('users:detail', pk=pk)


@require_POST
@login_required
@staff_member_required
def user_deactivate_view(request, pk):
    """
    Deactivate user with PRP override capability.
    Business Rule: PIMS admin can override PRP user status.
    """
    user_obj = get_object_or_404(CustomUser, pk=pk)
    
    try:
        user_obj.is_active = False
        user_obj.save()
        
        prp_note = ""
        if getattr(user_obj, 'is_prp_managed', False):
            prp_note = " (Admin override - user may still be active in PRP)"
        
        messages.success(
            request,
            f'User "{user_obj.get_full_name()}" deactivated successfully.{prp_note}'
        )
        
        logger.info(
            f'User {user_obj.employee_id} deactivated by {request.user.username}. '
            f'PRP managed: {getattr(user_obj, "is_prp_managed", False)}'
        )
        
    except Exception as e:
        logger.error(f'User deactivation failed: {str(e)}')
        messages.error(request, 'Failed to deactivate user. Please try again.')
    
    return redirect('users:detail', pk=pk)

# ============================================================================
# USER PROFILE MANAGEMENT
# ============================================================================

@method_decorator(login_required, name='dispatch')
class UserProfileView(DetailView):
    """User profile view for logged-in user"""
    model = CustomUser
    template_name = 'users/user_profile.html'
    context_object_name = 'user_obj'
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        
        context.update({
            'page_title': 'My Profile',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'is_prp_managed': getattr(user_obj, 'is_prp_managed', False),
            'prp_readonly_notice': (
                'Some fields are managed by PRP and cannot be edited.'
                if getattr(user_obj, 'is_prp_managed', False) else None
            ),
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class UserProfileEditView(UpdateView):
    """User profile edit view with PRP field protection"""
    model = CustomUser
    fields = ['first_name', 'last_name', 'phone_number', 'profile_image', 'notes']
    template_name = 'users/user_profile_edit.html'
    success_url = reverse_lazy('users:profile')
    
    def get_object(self):
        return self.request.user
    
    def get_form(self, form_class=None):
        """Customize form for PRP users"""
        form = super().get_form(form_class)
        
        # For PRP users, make certain fields read-only
        if getattr(self.request.user, 'is_prp_managed', False):
            prp_readonly_fields = ['first_name', 'last_name', 'phone_number']
            
            for field_name in prp_readonly_fields:
                if field_name in form.fields:
                    form.fields[field_name].widget.attrs['readonly'] = True
                    form.fields[field_name].help_text = 'Managed by PRP - cannot be edited'
        
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context.update({
            'page_title': 'Edit Profile',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'is_prp_managed': getattr(self.request.user, 'is_prp_managed', False),
        })
        
        return context

# ============================================================================
# SEARCH, REPORTING, AND ANALYTICS
# ============================================================================

@method_decorator(login_required, name='dispatch')
class UserSearchView(ListView):
    """Advanced user search with PRP filtering"""
    model = CustomUser
    template_name = 'users/user_search.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if not query:
            return CustomUser.objects.none()
        
        # Advanced search across multiple fields
        return CustomUser.objects.filter(
            Q(employee_id__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(office__icontains=query) |
            Q(designation__icontains=query) |
            Q(phone_number__icontains=query)
        ).order_by('employee_id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context.update({
            'page_title': 'User Search',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'search_query': self.request.GET.get('q', ''),
        })
        
        return context


@login_required
def user_lookup_by_employee_id(request, employee_id):
    """
    AJAX endpoint for employee ID lookup (supports both local and PRP users).
    Used for quick user verification and autocomplete features.
    """
    try:
        user = CustomUser.objects.get(employee_id=employee_id)
        
        user_data = {
            'found': True,
            'user_id': user.id,
            'employee_id': user.employee_id,
            'full_name': user.get_full_name(),
            'email': user.email,
            'office': user.office,
            'designation': user.designation,
            'is_active': user.is_active,
            'is_prp_managed': getattr(user, 'is_prp_managed', False),
            'profile_url': reverse('users:detail', kwargs={'pk': user.pk}),
        }
        
        return JsonResponse(user_data)
        
    except CustomUser.DoesNotExist:
        # Check if this might be a PRP user not yet synced
        try:
            sync_service = PRPSyncService()
            prp_user_data = sync_service.check_prp_user_exists(employee_id)
            
            if prp_user_data:
                return JsonResponse({
                    'found': False,
                    'prp_exists': True,
                    'message': 'User exists in PRP but not synced to PIMS yet.',
                    'prp_data': {
                        'name': prp_user_data.get('nameEng', ''),
                        'designation': prp_user_data.get('designationEng', ''),
                        'email': prp_user_data.get('email', ''),
                    }
                })
        except Exception as e:
            logger.error(f'PRP lookup failed for {employee_id}: {str(e)}')
        
        return JsonResponse({
            'found': False,
            'prp_exists': False,
            'message': 'User not found in PIMS or PRP.'
        })


@method_decorator(login_required, name='dispatch')
class UserReportsView(TemplateView):
    """
    User reports and analytics with PRP integration.
    Provides insights into user distribution, sync status, and trends.
    """
    template_name = 'users/user_reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Generate comprehensive user statistics
        user_stats = self._generate_user_statistics()
        prp_analytics = self._generate_prp_analytics()
        office_breakdown = self._generate_office_breakdown()
        
        context.update({
            'page_title': 'User Reports & Analytics',
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time': timezone.now(),
            'generated': timezone.now(),
            'user_stats': user_stats,
            'prp_analytics': prp_analytics,
            'office_breakdown': office_breakdown,
            'days_options': [7, 15, 30, 60, 90],
            'selected_days': self.request.GET.get('days', 30)
        })

        # Handle CSV export
        if self.request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="user_report_{timezone.now().date()}.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Employee ID', 'Full Name', 'Email', 'Office', 'Designation',
                'Is Active', 'Is PRP Managed', 'Last Sync', 'Created At'
            ])
            
            users = CustomUser.objects.all()
            for user in users:
                writer.writerow([
                    user.employee_id,
                    user.get_full_name(),
                    user.email,
                    user.office,
                    user.designation,
                    'Active' if user.is_active else 'Inactive',
                    'Yes' if getattr(user, 'is_prp_managed', False) else 'No',
                    user.prp_last_sync.strftime('%Y-%m-%d %H:%M:%S') if getattr(user, 'prp_last_sync', None) else '',
                    user.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            return response

        return context
    
    def _generate_user_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive user statistics"""
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'activity_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0,
        }
    
    def _generate_prp_analytics(self) -> Dict[str, Any]:
        """Generate PRP-specific analytics"""
        if not hasattr(CustomUser, 'is_prp_managed'):
            return {'enabled': False}
        
        total_users = CustomUser.objects.count()
        prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
        local_users = total_users - prp_users
        
        # Sync status analysis
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        prp_queryset = CustomUser.objects.filter(is_prp_managed=True)
        never_synced = prp_queryset.filter(prp_last_sync__isnull=True).count()
        recently_synced = prp_queryset.filter(prp_last_sync__gte=week_ago).count()
        needs_sync = prp_queryset.filter(prp_last_sync__lt=month_ago).count()
        
        return {
            'enabled': True,
            'total_prp_users': prp_users,
            'total_local_users': local_users,
            'prp_percentage': round((prp_users / total_users * 100), 2) if total_users > 0 else 0,
            'never_synced': never_synced,
            'recently_synced': recently_synced,
            'needs_sync': needs_sync,
            'sync_health': 'good' if needs_sync < (prp_users * 0.1) else 'warning',
        }
    
    def _generate_office_breakdown(self) -> List[Dict[str, Any]]:
        """Generate office-wise user breakdown"""
        office_stats = CustomUser.objects.values('office').annotate(
            total=Count('id'),
            active=Count(Case(When(is_active=True, then=1), output_field=IntegerField())),
            prp_managed=Count(Case(
                When(is_prp_managed=True, then=1) if hasattr(CustomUser, 'is_prp_managed') else When(id__gt=0, then=0),
                output_field=IntegerField()
            ))
        ).order_by('-total')
        
        return list(office_stats)

# ============================================================================
# AJAX API ENDPOINTS
# ============================================================================

@require_GET
@login_required
def get_user_info_ajax(request, user_id):
    """Get user information via AJAX"""
    try:
        user = CustomUser.objects.get(id=user_id)
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'employee_id': user.employee_id,
                'full_name': user.get_full_name(),
                'email': user.email,
                'office': user.office,
                'designation': user.designation,
                'is_active': user.is_active,
                'is_prp_managed': getattr(user, 'is_prp_managed', False),
                'created_at': user.created_at.isoformat(),
                'updated_at': user.updated_at.isoformat(),
            }
        })
        
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})


@require_GET
@login_required
def validate_employee_id_ajax(request):
    """Validate employee ID availability via AJAX"""
    employee_id = request.GET.get('employee_id', '')
    
    if not employee_id:
        return JsonResponse({'valid': False, 'message': 'Employee ID is required'})
    
    # Check if employee ID already exists
    exists = CustomUser.objects.filter(employee_id=employee_id).exists()
    
    if exists:
        return JsonResponse({
            'valid': False,
            'message': 'Employee ID already exists in PIMS'
        })
    
    # Check if it's a potential PRP user
    if employee_id.startswith('prp_') or (employee_id.isdigit() and len(employee_id) >= 6):
        return JsonResponse({
            'valid': False,
            'message': 'This appears to be a PRP Employee ID. Use PRP sync instead.',
            'suggestion': 'prp_sync'
        })
    
    return JsonResponse({'valid': True, 'message': 'Employee ID is available'})


@require_GET
@login_required
@staff_member_required
def check_prp_user_exists(request, employee_id):
    """Check if user exists in PRP via AJAX"""
    try:
        sync_service = PRPSyncService()
        prp_data = sync_service.check_prp_user_exists(employee_id)
        
        if prp_data:
            return JsonResponse({
                'exists': True,
                'user_data': {
                    'name': prp_data.get('nameEng', ''),
                    'designation': prp_data.get('designationEng', ''),
                    'email': prp_data.get('email', ''),
                    'status': prp_data.get('status', ''),
                },
                'can_sync': True
            })
        else:
            return JsonResponse({
                'exists': False,
                'message': 'User not found in PRP'
            })
            
    except PRPConnectionError as e:
        return JsonResponse({
            'exists': False,
            'error': 'PRP connection failed',
            'message': str(e)
        })
    except Exception as e:
        logger.error(f'PRP user check failed: {str(e)}')
        return JsonResponse({
            'exists': False,
            'error': 'Unexpected error',
            'message': 'Please try again later'
        })


@require_GET
@login_required
@staff_member_required
def get_prp_departments_ajax(request):
    """Get PRP departments via AJAX"""
    try:
        prp_client = PRPClient()
        departments = prp_client.get_departments()
        
        return JsonResponse({
            'success': True,
            'departments': departments
        })
        
    except Exception as e:
        logger.error(f'Failed to fetch PRP departments: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch departments from PRP'
        })

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_prp_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """Helper function to fetch PRP user data with error handling"""
    try:
        sync_service = PRPSyncService()
        return sync_service.get_user_data_from_prp(user_id)
    except Exception as e:
        logger.error(f'Failed to fetch PRP data for user {user_id}: {str(e)}')
        return None


def sync_single_prp_user(employee_id: str, department_id: Optional[int] = None) -> Dict[str, Any]:
    """Helper function to sync a single PRP user"""
    try:
        sync_service = PRPSyncService()
        result = sync_service.sync_single_user(employee_id, department_id)
        return {'success': True, 'result': result}
    except Exception as e:
        logger.error(f'Failed to sync PRP user {employee_id}: {str(e)}')
        return {'success': False, 'error': str(e)}


# ============================================================================
# LEGACY VIEW ALIASES (for backward compatibility)
# ============================================================================

@method_decorator(login_required, name='dispatch')
class UserListViewLegacy(UserListView):
    """Legacy alias for UserListView"""
    pass


@method_decorator(login_required, name='dispatch')
class UserDetailViewLegacy(UserDetailView):
    """Legacy alias for UserDetailView"""
    pass


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserCreateViewLegacy(UserCreateView):
    """Legacy alias for UserCreateView"""
    pass


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserUpdateViewLegacy(UserUpdateView):
    """Legacy alias for UserUpdateView"""
    pass


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserDeleteViewLegacy(UserDeleteView):
    """Legacy alias for UserDeleteView"""
    pass