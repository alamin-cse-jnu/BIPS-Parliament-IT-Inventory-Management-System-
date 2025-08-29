"""
Views for Users app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat, Dhaka

This module provides complete user management with real PRP (Parliament Resource Portal) integration.
It combines core user management functionality with real-time PRP API synchronization,
removing all mock data functionality and adhering to specified business rules.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Manage user authentication, CRUD operations, and PRP synchronization
Business Rules:
- No user creation from PIMS: All users originate from PRP
- Read-only PRP data: Information from PRP API cannot be edited in PIMS
- Admin sync control: Only admin can update/sync users from PRP
- Status override: PIMS admin inactive status takes precedence
- Username format: prp_{userId} for Django username field
- Default password: "12345678" for all PRP-created users
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
)
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q, Count, Case, When, IntegerField
from django.core.paginator import Paginator
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.safestring import mark_safe
from django.conf import settings

from .models import CustomUser
from devices.models import Device
from assignments.models import Assignment
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, UserProfileForm,
    UserSearchForm, UserLoginForm, PasswordResetForm, BulkUserActionForm,
    UserDeactivationForm
)
from .api.prp_client import PRPClient, create_prp_client
from .api.sync_service import PRPSyncService, PRPSyncResult
from .api.exceptions import (
    PRPException, PRPConnectionError, PRPAuthenticationError,
    PRPSyncError, PRPDataValidationError, PRPBusinessRuleError, PRPConfigurationError
)

# Configure logging
logger = logging.getLogger('pims.users.views')

# ============================================================================
# Base Classes and Mixins
# ============================================================================

class PRPAwareMixin:
    """Mixin to provide PRP integration context to views."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'prp_integration_enabled': True,
            'location_context': 'Bangladesh Parliament Secretariat, Dhaka',
            'current_time_dhaka': timezone.now().astimezone(timezone.get_current_timezone()),
        })
        
        # Add PRP statistics
        if hasattr(CustomUser, 'is_prp_managed'):
            total_users = CustomUser.objects.count()
            prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
            local_users = total_users - prp_users
            
            context.update({
                'prp_stats': {
                    'total_users': total_users,
                    'prp_users': prp_users,
                    'local_users': local_users,
                    'prp_percentage': round((prp_users / total_users * 100), 1) if total_users > 0 else 0
                }
            })
        
        return context


class AdminOnlyMixin(PermissionRequiredMixin):
    """Restrict access to admin users only for PRP operations."""
    permission_required = 'auth.add_user'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Only admin users can perform PRP operations.")
        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# Authentication Views
# ============================================================================

class CustomLoginView(LoginView):
    """Custom login view supporting PRP User ID login."""
    form_class = UserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        """Handle successful login with PRP user detection."""
        user = form.get_user()
        login(self.request, user)
        
        # Set session timeout based on remember_me
        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)  # Session expires when browser closes
        
        # Enhanced welcome message for PRP users
        welcome_msg = (
            f'Welcome back, {user.get_display_name()}! (PRP User)'
            if getattr(user, 'is_prp_managed', False)
            else f'Welcome back, {user.get_display_name()}!'
        )
        
        logger.info(
            f"User login: {user.username} ({user.employee_id})",
            extra={
                'user_id': user.id,
                'employee_id': user.employee_id,
                'is_prp_managed': getattr(user, 'is_prp_managed', False),
                'login_time': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            }
        )
        
        messages.success(self.request, welcome_msg)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add PRP integration context to login page."""
        context = super().get_context_data(**kwargs)
        context.update({
            'prp_integration_enabled': True,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        })
        return context


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view with PRP user handling."""
    form_class = PasswordResetForm
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')

    def form_valid(self, form):
        """Handle PRP users appropriately."""
        email = form.cleaned_data['email']
        
        try:
            user = CustomUser.objects.get(email=email)
            if getattr(user, 'is_prp_managed', False):
                messages.warning(
                    self.request,
                    'Note: This user is managed by PRP. Password reset will use the default PRP password.'
                )
        except CustomUser.DoesNotExist:
            pass
        
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add Bangladesh context to password reset page."""
        context = super().get_context_data(**kwargs)
        context.update({
            'prp_integration_enabled': True,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        })
        return context


# ============================================================================
# User Management Views
# ============================================================================

class UserListView(LoginRequiredMixin, PRPAwareMixin, ListView):
    """User list view with PRP filtering and sync status."""
    model = CustomUser
    template_name = 'users/users_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        """Enhanced queryset with PRP status and filtering."""
        queryset = CustomUser.objects.select_related().annotate(
            assigned_devices_count=Count('device_assignments', distinct=True),
            is_prp_user=Case(
                When(is_prp_managed=True, then=1),
                default=0,
                output_field=IntegerField()
            )
        )
        
        form = UserSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            office = form.cleaned_data.get('office')
            designation = form.cleaned_data.get('designation')
            group = form.cleaned_data.get('group')
            is_active = form.cleaned_data.get('is_active')
            is_staff = form.cleaned_data.get('is_staff')
            user_source = form.cleaned_data.get('user_source')
            sync_status = form.cleaned_data.get('sync_status')
            
            # Basic search
            if search:
                queryset = queryset.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(username__icontains=search) |
                    Q(email__icontains=search) |
                    Q(employee_id__icontains=search)
                )
            
            # Office/department filter
            if office:
                queryset = queryset.filter(office__icontains=office)
            
            # Designation filter
            if designation:
                queryset = queryset.filter(designation__icontains=designation)
            
            # Role/group filter
            if group:
                queryset = queryset.filter(groups=group)
            
            # Active status filter
            if is_active:
                queryset = queryset.filter(is_active=(is_active == 'true'))
            
            # Staff status filter
            if is_staff:
                queryset = queryset.filter(is_staff=(is_staff == 'true'))
            
            # PRP user source filter
            if user_source:
                if user_source == 'prp':
                    queryset = queryset.filter(is_prp_managed=True)
                elif user_source == 'local':
                    queryset = queryset.filter(is_prp_managed=False)
            
            # PRP sync status filter
            if sync_status and hasattr(CustomUser, 'is_prp_managed'):
                now = timezone.now()
                if sync_status == 'never_synced':
                    queryset = queryset.filter(
                        is_prp_managed=True,
                        prp_last_sync__isnull=True
                    )
                elif sync_status == 'recently_synced':
                    yesterday = now - timedelta(hours=24)
                    queryset = queryset.filter(
                        is_prp_managed=True,
                        prp_last_sync__gte=yesterday
                    )
                elif sync_status == 'needs_sync':
                    week_ago = now - timedelta(days=7)
                    queryset = queryset.filter(
                        is_prp_managed=True,
                        prp_last_sync__lt=week_ago
                    )
        
        return queryset.order_by('-is_prp_user', '-date_joined')
    
    def get_context_data(self, **kwargs):
        """Enhanced context with PRP statistics."""
        context = super().get_context_data(**kwargs)
        context['search_form'] = UserSearchForm(self.request.GET)
        
        # Add PRP sync statistics
        if hasattr(CustomUser, 'is_prp_managed'):
            total_users = CustomUser.objects.count()
            prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
            local_users = total_users - prp_users
            
            now = timezone.now()
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
                'total_users': total_users,
                'prp_users_count': prp_users,
                'local_users_count': local_users,
                'prp_sync_stats': {
                    'never_synced': never_synced,
                    'recently_synced': recently_synced,
                    'needs_sync': needs_sync,
                }
            })
        
        return context


class UserDetailView(LoginRequiredMixin, PRPAwareMixin, DetailView):
    """User detail view with PRP sync information."""
    model = CustomUser
    template_name = 'users/users_detail.html'
    context_object_name = 'user'
    permission_required = 'auth.view_user'
    
    def get_context_data(self, **kwargs):
        """Enhanced context with PRP sync status and assignments."""
        context = super().get_context_data(**kwargs)
        user = self.object
        
        # PRP-specific context
        context.update({
            'is_prp_user': getattr(user, 'is_prp_managed', False),
            'prp_last_sync': getattr(user, 'prp_last_sync', None),
            'readonly_fields': [
                'employee_id', 'first_name', 'last_name', 'email',
                'designation', 'office', 'phone_number'
            ] if getattr(user, 'is_prp_managed', False) else []
        })
        
        # Assignment information
        try:
            active_assignments = Assignment.objects.filter(
                assigned_to=user,
                is_active=True,
                status='ASSIGNED'
            ).select_related('device', 'assigned_location').order_by('-assigned_date')
            
            assignment_history = Assignment.objects.filter(
                assigned_to=user
            ).select_related('device', 'assigned_location').order_by('-assigned_date')[:10]
            
            total_assignments = Assignment.objects.filter(assigned_to=user).count()
            returned_assignments = Assignment.objects.filter(
                assigned_to=user, 
                status='RETURNED'
            ).count()
            overdue_assignments = Assignment.objects.filter(
                assigned_to=user,
                status='ASSIGNED',
                expected_return_date__lt=timezone.now().date()
            ).count()
            
            context.update({
                'active_assignments': active_assignments,
                'assignment_history': assignment_history,
                'total_assignments': total_assignments,
                'returned_assignments': returned_assignments,
                'overdue_assignments': overdue_assignments,
            })
        except ImportError:
            context.update({
                'active_assignments': [],
                'assignment_history': [],
                'total_assignments': 0,
                'returned_assignments': 0,
                'overdue_assignments': 0,
            })
        
        return context


class UserCreateView(LoginRequiredMixin, AdminOnlyMixin, PRPAwareMixin, CreateView):
    """User creation view restricted to local PIMS users."""
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'users/users_create.html'
    permission_required = 'auth.add_user'
    success_url = reverse_lazy('users:list')
    
    def get_context_data(self, **kwargs):
        """Add PRP context to creation form."""
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Create Local PIMS User',
            'prp_warning': 'PRP users must be synced through the admin interface.',
            'creation_mode': 'local_only'
        })
        return context
    
    def form_valid(self, form):
        """Prevent PRP user creation and log local user creation."""
        try:
            user = form.save(commit=False)
            if form.cleaned_data.get('is_prp_managed', False):
                form.add_error(
                    None,
                    'PRP-managed users cannot be created manually. Use PRP synchronization.'
                )
                return self.form_invalid(form)
            
            user.is_prp_managed = False
            user.save()
            
            logger.info(
                f"Local user created: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'created_by': self.request.user.username,
                    'is_prp_managed': False,
                    'creation_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            
            messages.success(
                self.request,
                f'Local user "{user.get_display_name()}" created successfully.'
            )
            return super().form_valid(form)
        except IntegrityError as e:
            form.add_error(None, f"User creation failed: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Error creating local user: {e}")
            form.add_error(None, f"Unexpected error: {str(e)}")
            return self.form_invalid(form)


class UserUpdateView(LoginRequiredMixin, AdminOnlyMixin, PRPAwareMixin, UpdateView):
    """User update view with PRP field protection."""
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'users/users_edit.html'
    permission_required = 'auth.change_user'
    
    def get_success_url(self):
        return reverse('users:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        """Add PRP context to edit form."""
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        if getattr(user, 'is_prp_managed', False):
            context.update({
                'is_prp_user': True,
                'readonly_warning': True,
                'prp_last_sync': getattr(user, 'prp_last_sync', None),
                'readonly_fields': [
                    'employee_id', 'first_name', 'last_name', 'email',
                    'designation', 'office', 'phone_number'
                ]
            })
        
        return context
    
    def form_valid(self, form):
        """Enforce PRP field restrictions."""
        user = form.instance
        
        if getattr(user, 'is_prp_managed', False):
            logger.info(
                f"PRP user modified: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'modified_by': self.request.user.username,
                    'is_prp_managed': True,
                    'modification_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            messages.warning(
                self.request,
                f'PRP user "{user.get_display_name()}" updated. Only administrative fields modified.'
            )
        else:
            messages.success(
                self.request,
                f'Local user "{user.get_display_name()}" updated successfully.'
            )
        
        return super().form_valid(form)


class UserDeleteView(LoginRequiredMixin, AdminOnlyMixin, View):
    """User deletion view with PRP protection."""
    permission_required = 'auth.delete_user'
    
    def get(self, request, pk):
        """Display delete confirmation page."""
        user = get_object_or_404(CustomUser, pk=pk)
        
        if user == request.user:
            messages.error(
                request,
                'You cannot delete your own account.'
            )
            return redirect('users:list')
        
        context = {
            'object': user,
            'is_prp_user': getattr(user, 'is_prp_managed', False),
            'prp_warning': (
                'This is a PRP-managed user. Deletion will remove them from PIMS, '
                'but they may be recreated during the next PRP synchronization.'
            ) if getattr(user, 'is_prp_managed', False) else None,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        }
        
        return render(request, 'users/users_delete.html', context)
    
    def post(self, request, pk):
        """Handle user deletion with PRP protection."""
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            if user == request.user:
                messages.error(
                    request,
                    'You cannot delete your own account.'
                )
                return redirect('users:list')
            
            is_prp_user = getattr(user, 'is_prp_managed', False)
            if is_prp_user:
                messages.error(
                    request,
                    'Cannot delete PRP-managed user. Use deactivation instead.'
                )
                return redirect('users:detail', pk=user.pk)
            
            user_name = user.get_display_name()
            logger.warning(
                f"User deleted: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'deleted_by': request.user.username,
                    'is_prp_managed': is_prp_user,
                    'deletion_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            
            user.delete()
            messages.success(
                request,
                f'Local user "{user_name}" has been permanently deleted.'
            )
            return redirect('users:list')
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            messages.error(request, f'Error deleting user: {str(e)}')
            return redirect('users:list')


class UserDeactivateView(LoginRequiredMixin, AdminOnlyMixin, UpdateView):
    """User deactivation view with PRP business rule handling."""
    model = CustomUser
    template_name = 'users/user_deactivate_confirm.html'
    permission_required = 'auth.change_user'
    fields = []
    
    def get_success_url(self):
        return reverse('users:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        context.update({
            'page_title': f'Deactivate User: {user.get_display_name()}',
            'is_prp_user': getattr(user, 'is_prp_managed', False),
            'prp_last_sync': getattr(user, 'prp_last_sync', None),
            'admin_override_note': getattr(user, 'is_prp_managed', False)
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle user deactivation with PRP business rules."""
        user = self.get_object()
        
        try:
            if user == request.user:
                messages.error(
                    request,
                    'You cannot deactivate your own account.'
                )
                return redirect('users:detail', pk=user.pk)
            
            user.is_active = False
            user.save(update_fields=['is_active'])
            
            is_prp_user = getattr(user, 'is_prp_managed', False)
            logger.info(
                f"User deactivated: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'deactivated_by': request.user.username,
                    'is_prp_managed': is_prp_user,
                    'admin_override': is_prp_user,
                    'deactivation_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            
            message = f'User "{user.get_display_name()}" has been deactivated.'
            if is_prp_user:
                message += ' Note: This is an admin override for a PRP-managed user.'
            
            messages.success(request, message)
            return redirect('users:detail', pk=user.pk)
            
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            messages.error(request, f'Error deactivating user: {str(e)}')
            return redirect('users:detail', pk=user.pk)


class UserProfileView(LoginRequiredMixin, PRPAwareMixin, UpdateView):
    """User profile view with PRP integration awareness."""
    model = CustomUser
    form_class = UserProfileForm
    template_name = 'users/profile.html'
    
    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        return reverse('users:profile')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        if getattr(user, 'is_prp_managed', False):
            context.update({
                'is_prp_user': True,
                'prp_last_sync': getattr(user, 'prp_last_sync', None),
                'readonly_fields': [
                    'employee_id', 'first_name', 'last_name', 'email',
                    'designation', 'office', 'phone_number'
                ],
                'profile_note': 'Your profile data is managed by PRP. Contact system administrator for updates.'
            })
        
        context.update({
            'assigned_devices_count': Device.objects.filter(
                assignments__user=user,
                assignments__is_active=True
            ).distinct().count(),
            'total_assignments_count': Assignment.objects.filter(user=user).count(),
            'last_login_formatted': user.last_login.strftime('%B %d, %Y at %I:%M %p') if user.last_login else 'Never'
        })
        
        return context
    
    def form_valid(self, form):
        """Handle PRP user profile restrictions."""
        user = form.instance
        
        if getattr(user, 'is_prp_managed', False):
            logger.info(
                f"PRP user profile modified: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'is_prp_managed': True,
                    'modification_time': timezone.now().isoformat(),
                    'modified_fields': form.changed_data,
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            messages.info(
                self.request,
                'Profile updated. Note: Core information is managed by PRP and cannot be changed here.'
            )
        else:
            messages.success(
                self.request,
                'Your profile has been updated successfully.'
            )
        
        return super().form_valid(form)


# ============================================================================
# PRP Synchronization Views
# ============================================================================

class PRPSyncDashboardView(LoginRequiredMixin, AdminOnlyMixin, PRPAwareMixin, TemplateView):
    """PRP synchronization dashboard for admin users."""
    template_name = 'users/prp_sync_dashboard.html'
    
    def get_context_data(self, **kwargs):
        """Provide comprehensive PRP sync dashboard context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'PRP Sync Dashboard - Bangladesh Parliament Secretariat'
        
        try:
            prp_client = PRPClient()
            sync_service = PRPSyncService(prp_client)
            
            api_status = sync_service.check_api_health()
            sync_stats = sync_service.get_sync_statistics()
            recent_operations = sync_service.get_recent_operations(limit=10)
            
            context.update({
                'api_status': api_status,
                'sync_stats': sync_stats,
                'recent_operations': recent_operations,
                'prp_base_url': settings.PRP_API_BASE_URL,
                'last_update': timezone.now(),
                'cached_departments_count': len(sync_service.get_departments()),
                'last_sync_time': sync_service.get_last_sync_time()
            })
            
        except PRPConnectionError as e:
            logger.error(f"PRP connection error in dashboard: {e}")
            context.update({
                'api_status': {'connected': False, 'error': str(e)},
                'connection_error': True
            })
        except Exception as e:
            logger.error(f"Unexpected error in PRP dashboard: {e}")
            context.update({
                'system_error': True,
                'error_message': str(e)
            })
        
        return context


class PRPSyncUsersView(LoginRequiredMixin, AdminOnlyMixin, PRPAwareMixin, TemplateView):
    """PRP user synchronization interface."""
    template_name = 'users/prp_sync_users.html'
    
    def get_context_data(self, **kwargs):
        """Provide context for sync interface."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'PRP User Synchronization'
        
        try:
            prp_client = PRPClient()
            sync_service = PRPSyncService(prp_client)
            departments = sync_service.get_departments()
            
            context.update({
                'departments': departments,
                'sync_options': {
                    'dry_run': True,
                    'force_update': False,
                    'sync_inactive': True
                }
            })
            
        except PRPConnectionError as e:
            logger.error(f"PRP connection error: {e}")
            context['connection_error'] = str(e)
        except Exception as e:
            logger.error(f"Error loading sync interface: {e}")
            context['system_error'] = str(e)
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle PRP sync operations."""
        try:
            sync_type = request.POST.get('sync_type', 'department')
            department_id = request.POST.get('department_id')
            dry_run = request.POST.get('dry_run') == 'on'
            force_update = request.POST.get('force_update') == 'on'
            
            prp_client = PRPClient()
            sync_service = PRPSyncService(prp_client)
            
            with transaction.atomic():
                savepoint = transaction.savepoint()
                try:
                    if sync_type == 'all_departments':
                        result = sync_service.sync_all_departments(
                            dry_run=dry_run,
                            force_update=force_update
                        )
                    elif sync_type == 'department' and department_id:
                        result = sync_service.sync_department_users(
                            department_id=int(department_id),
                            dry_run=dry_run,
                            force_update=force_update
                        )
                    else:
                        raise PRPBusinessRuleError('Invalid sync parameters')
                    
                    if not dry_run and not result.success:
                        transaction.savepoint_rollback(savepoint)
                        raise PRPSyncError("Sync failed", details=result.errors)
                    
                    message = (
                        f"Dry Run: Would process {result.users_created + result.users_updated} users"
                        if dry_run else
                        f"Sync completed: Created {result.users_created}, Updated {result.users_updated}"
                    )
                    messages.success(request, message)
                    
                    if not dry_run:
                        transaction.savepoint_commit(savepoint)
                    
                    logger.info(
                        f"PRP sync completed: {sync_type}",
                        extra={
                            'sync_type': sync_type,
                            'department_id': department_id,
                            'dry_run': dry_run,
                            'initiated_by': request.user.username,
                            'result': {
                                'users_created': result.users_created,
                                'users_updated': result.users_updated,
                                'errors': result.errors
                            },
                            'sync_time': timezone.now().isoformat(),
                            'location': 'Bangladesh Parliament Secretariat, Dhaka'
                        }
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'result': {
                            'users_created': result.users_created,
                            'users_updated': result.users_updated,
                            'users_unchanged': result.users_unchanged,
                            'errors': result.errors,
                            'departments_processed': getattr(result, 'departments_processed', 1)
                        }
                    })
                    
                except Exception as e:
                    if not dry_run:
                        transaction.savepoint_rollback(savepoint)
                    raise
                
        except PRPConnectionError as e:
            logger.error(f"PRP connection error during sync: {e}")
            messages.error(request, f'PRP connection failed: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': f'PRP connection failed: {str(e)}'
            }, status=503)
        except PRPBusinessRuleError as e:
            logger.warning(f"PRP business rule violation: {e}")
            messages.error(request, f'Business rule violation: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': f'Business rule violation: {str(e)}'
            }, status=400)
        except Exception as e:
            logger.error(f"Unexpected error during PRP sync: {e}")
            messages.error(request, f'Sync operation failed: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': f'Sync operation failed: {str(e)}'
            }, status=500)


@require_POST
@login_required
@staff_member_required
def prp_trigger_sync_ajax(request):
    """AJAX endpoint for PRP sync operations."""
    try:
        data = json.loads(request.body)
        operation = data.get('operation')
        params = data.get('params', {})
        
        prp_client = PRPClient()
        sync_service = PRPSyncService(prp_client)
        
        if operation == 'health_check':
            result = sync_service.check_api_health()
        elif operation == 'sync_department':
            department_id = params.get('department_id')
            result = sync_service.sync_department_users(
                department_id=department_id,
                dry_run=params.get('dry_run', False)
            )
        elif operation == 'sync_all':
            result = sync_service.sync_all_departments(
                dry_run=params.get('dry_run', False)
            )
        elif operation == 'get_departments':
            result = sync_service.get_departments()
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown operation: {operation}'
            }, status=400)
        
        logger.info(
            f"PRP AJAX sync operation: {operation}",
            extra={
                'operation': operation,
                'params': params,
                'initiated_by': request.user.username,
                'sync_time': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            }
        )
        
        return JsonResponse({
            'success': True,
            'data': result,
            'timestamp': timezone.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except PRPConnectionError as e:
        logger.error(f"PRP connection error in AJAX: {e}")
        return JsonResponse({
            'success': False,
            'error': f'PRP connection failed: {str(e)}'
        }, status=503)
    except Exception as e:
        logger.error(f"Error in PRP AJAX operation: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Operation failed: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
@login_required
@staff_member_required
def prp_user_lookup_ajax(request):
    """AJAX endpoint for PRP user lookup."""
    try:
        employee_id = request.GET.get('employee_id')
        if not employee_id:
            return JsonResponse({
                'success': False,
                'error': 'Employee ID required'
            }, status=400)
        
        prp_client = PRPClient()
        prp_user_data = prp_client.lookup_user_by_employee_id(employee_id)
        
        if prp_user_data:
            try:
                local_user = CustomUser.objects.get(employee_id=employee_id)
                user_data = {
                    'exists_locally': True,
                    'local_user': {
                        'id': local_user.id,
                        'username': local_user.username,
                        'is_prp_managed': getattr(local_user, 'is_prp_managed', False),
                        'last_sync': getattr(local_user, 'prp_last_sync', None),
                        'is_active': local_user.is_active
                    },
                    'prp_data': prp_user_data
                }
            except CustomUser.DoesNotExist:
                user_data = {
                    'exists_locally': False,
                    'prp_data': prp_user_data
                }
            
            return JsonResponse({
                'success': True,
                'data': user_data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Employee ID {employee_id} not found in PRP'
            }, status=404)
            
    except PRPConnectionError as e:
        logger.error(f"PRP connection error in lookup: {e}")
        return JsonResponse({
            'success': False,
            'error': f'PRP connection failed: {str(e)}'
        }, status=503)
    except Exception as e:
        logger.error(f"Error in PRP user lookup: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Lookup failed: {str(e)}'
        }, status=500)


@require_http_methods(["GET", "POST"])
@login_required
@staff_member_required
def prp_sync_departments(request):
    """View to sync and refresh departments from PRP API."""
    context = {
        'page_title': 'PRP Department Synchronization',
        'breadcrumb_items': [
            {'name': 'Users', 'url': reverse('users:list')},
            {'name': 'PRP Integration', 'url': '#'},
            {'name': 'Sync Departments', 'url': ''},
        ]
    }
    
    if request.method == 'POST':
        try:
            prp_client = PRPClient()
            sync_service = PRPSyncService(prp_client)
            
            force_sync = request.POST.get('force_sync', False) == 'on'
            dry_run = request.POST.get('dry_run', False) == 'on'
            
            logger.info(
                f"Starting PRP department sync - Force: {force_sync}, Dry Run: {dry_run}",
                extra={'user': request.user.username, 'location': 'Bangladesh Parliament Secretariat, Dhaka'}
            )
            
            with transaction.atomic():
                savepoint = transaction.savepoint()
                try:
                    dept_result = sync_service.sync_departments(force_refresh=force_sync)
                    
                    if not dry_run and not dept_result.success:
                        transaction.savepoint_rollback(savepoint)
                        raise PRPSyncError("Department sync failed", details=dept_result.errors)
                    
                    message = (
                        f"Dry Run Complete: Would sync {dept_result.departments_processed} departments"
                        if dry_run else
                        f"Successfully synced {dept_result.departments_processed} departments from PRP"
                    )
                    messages.success(request, message)
                    context['sync_result'] = dept_result
                    
                    if not dry_run:
                        transaction.savepoint_commit(savepoint)
                
                except Exception as e:
                    if not dry_run:
                        transaction.savepoint_rollback(savepoint)
                    raise
                
        except (PRPConnectionError, PRPAuthenticationError, PRPSyncError) as e:
            logger.error(f"PRP error during department sync: {e}")
            messages.error(request, f'Department sync failed: {str(e)}')
        except Exception as e:
            logger.error(f"Unexpected error during department sync: {e}", exc_info=True)
            messages.error(request, f'Department sync failed: {str(e)}')
    
    try:
        from django.core.cache import cache
        cached_departments = cache.get('prp_departments', [])
        last_sync_time = cache.get('prp_departments_last_sync')
        
        context.update({
            'cached_departments_count': len(cached_departments),
            'last_sync_time': last_sync_time,
            'cache_expired': (
                not last_sync_time or 
                (timezone.now() - last_sync_time).total_seconds() > 86400
            ),
            'departments_sample': cached_departments[:5] if cached_departments else []
        })
    except Exception as e:
        logger.warning(f"Could not get department cache status: {e}")
        context['cache_error'] = str(e)
    
    return render(request, 'users/prp_sync_departments.html', context)


@require_POST
@login_required
@staff_member_required
def prp_departments_refresh(request):
    """AJAX endpoint to refresh department cache from PRP API."""
    try:
        prp_client = PRPClient()
        sync_service = PRPSyncService(prp_client)
        
        result = sync_service.sync_departments(force_refresh=True)
        
        if result.success:
            logger.info(
                f"Department refresh completed",
                extra={
                    'initiated_by': request.user.username,
                    'departments_processed': result.departments_processed,
                    'sync_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            return JsonResponse({
                'success': True,
                'message': f'Refreshed {result.departments_processed} departments',
                'departments_count': result.departments_processed,
                'timestamp': timezone.now().isoformat()
            })
        else:
            logger.error(f"Department refresh failed: {result.errors}")
            return JsonResponse({
                'success': False,
                'error': 'Department refresh failed',
                'details': result.errors
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error during department refresh: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Department refresh failed: {str(e)}'
        }, status=500)


@require_http_methods(["GET", "POST"])
@login_required
@staff_member_required
def prp_bulk_sync_users(request):
    """View for bulk user synchronization from PRP."""
    context = {
        'page_title': 'PRP Bulk User Synchronization',
        'breadcrumb_items': [
            {'name': 'Users', 'url': reverse('users:list')},
            {'name': 'PRP Integration', 'url': '#'},
            {'name': 'Bulk Sync Users', 'url': ''},
        ]
    }
    
    if request.method == 'POST':
        try:
            prp_client = PRPClient()
            sync_service = PRPSyncService(prp_client)
            
            selected_departments = request.POST.getlist('departments', [])
            sync_all = request.POST.get('sync_all', False) == 'on'
            force_sync = request.POST.get('force_sync', False) == 'on'
            dry_run = request.POST.get('dry_run', False) == 'on'
            update_inactive = request.POST.get('update_inactive', False) == 'on'
            
            if not sync_all and not selected_departments:
                messages.error(request, 'Please select departments to sync or choose "Sync All"')
                return render(request, 'users/prp_bulk_sync_users.html', context)
            
            logger.info(
                f"Starting bulk PRP user sync",
                extra={
                    'user': request.user.username,
                    'departments': selected_departments if not sync_all else 'ALL',
                    'force_sync': force_sync,
                    'dry_run': dry_run,
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            
            with transaction.atomic():
                savepoint = transaction.savepoint()
                try:
                    if sync_all:
                        sync_result = sync_service.sync_all_departments(
                            force_sync=force_sync,
                            update_inactive_users=update_inactive,
                            dry_run=dry_run
                        )
                    else:
                        sync_result = sync_service.sync_multiple_departments(
                            department_ids=[int(d) for d in selected_departments if d.isdigit()],
                            force_sync=force_sync,
                            update_inactive_users=update_inactive,
                            dry_run=dry_run
                        )
                    
                    if not dry_run and not sync_result.success:
                        transaction.savepoint_rollback(savepoint)
                        raise PRPSyncError("Bulk user sync failed", details=sync_result.errors)
                    
                    message = (
                        f"Dry Run Complete: Would process {sync_result.users_created + sync_result.users_updated} users "
                        f"from {sync_result.departments_processed} departments"
                        if dry_run else
                        f"Bulk sync completed successfully! Created: {sync_result.users_created}, "
                        f"Updated: {sync_result.users_updated}, Departments: {sync_result.departments_processed}"
                    )
                    messages.success(request, message)
                    context['sync_result'] = sync_result
                    
                    if not dry_run:
                        transaction.savepoint_commit(savepoint)
                    
                except Exception as e:
                    if not dry_run:
                        transaction.savepoint_rollback(savepoint)
                    raise
                
        except Exception as e:
            logger.error(f"Error during bulk sync: {e}", exc_info=True)
            messages.error(request, f'Bulk sync failed: {str(e)}')
    
    try:
        from django.core.cache import cache
        departments = cache.get('prp_departments', [])
        context['departments'] = departments
        
        context['sync_stats'] = {
            'total_users': CustomUser.objects.count(),
            'prp_users': CustomUser.objects.filter(is_prp_managed=True).count(),
            'never_synced': CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__isnull=True
            ).count(),
        }
        
    except Exception as e:
        logger.warning(f"Could not load departments or sync stats: {e}")
        context['departments'] = []
        context['load_error'] = str(e)
    
    return render(request, 'users/prp_bulk_sync_users.html', context)


@require_http_methods(["GET", "POST"])
@login_required
@staff_member_required
def prp_sync_department_users(request, department_id=None):
    """View to sync users from a specific PRP department."""
    context = {
        'page_title': 'Select Department for User Sync' if not department_id else f'PRP Department User Sync (Dept {department_id})',
        'breadcrumb_items': [
            {'name': 'Users', 'url': reverse('users:list')},
            {'name': 'PRP Integration', 'url': '#'},
            {'name': 'Department User Sync' if not department_id else f'Sync Dept {department_id}', 'url': ''},
        ]
    }
    
    if not department_id and request.method == 'GET':
        try:
            from django.core.cache import cache
            departments = cache.get('prp_departments', [])
            context['departments'] = departments
            return render(request, 'users/prp_select_department.html', context)
        except Exception as e:
            logger.error(f"Could not load departments: {e}")
            messages.error(request, f'Could not load departments: {str(e)}')
            return redirect('users:list')
    
    if not department_id and request.method == 'POST':
        department_id = request.POST.get('department_id')
        if not department_id:
            messages.error(request, 'Please select a department')
            return redirect('users:prp_sync_department_users')
    
    try:
        department_id = int(department_id)
    except (ValueError, TypeError):
        messages.error(request, 'Invalid department ID')
        return redirect('users:prp_sync_department_users')
    
    context['department_id'] = department_id
    
    if request.method == 'POST':
        try:
            prp_client = PRPClient()
            sync_service = PRPSyncService(prp_client)
            
            force_sync = request.POST.get('force_sync', False) == 'on'
            dry_run = request.POST.get('dry_run', False) == 'on'
            update_inactive = request.POST.get('update_inactive', False) == 'on'
            
            logger.info(
                f"Starting department user sync for department {department_id}",
                extra={
                    'user': request.user.username,
                    'department_id': department_id,
                    'force_sync': force_sync,
                    'dry_run': dry_run,
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            
            with transaction.atomic():
                savepoint = transaction.savepoint()
                try:
                    sync_result = sync_service.sync_department_users(
                        department_id=department_id,
                        force_sync=force_sync,
                        update_inactive_users=update_inactive,
                        dry_run=dry_run
                    )
                    
                    if not dry_run and not sync_result.success:
                        transaction.savepoint_rollback(savepoint)
                        raise PRPSyncError(f"Department {department_id} sync failed", details=sync_result.errors)
                    
                    message = (
                        f"Dry Run Complete: Would process {sync_result.users_created + sync_result.users_updated} users "
                        f"from department {department_id}"
                        if dry_run else
                        f"Department sync completed successfully! Created: {sync_result.users_created}, "
                        f"Updated: {sync_result.users_updated}, Skipped: {sync_result.users_skipped}"
                    )
                    messages.success(request, message)
                    context['sync_result'] = sync_result
                    
                    if not dry_run:
                        transaction.savepoint_commit(savepoint)
                
                except Exception as e:
                    if not dry_run:
                        transaction.savepoint_rollback(savepoint)
                    raise
                
        except Exception as e:
            logger.error(f"Error during department sync: {e}", exc_info=True)
            messages.error(request, f'Department sync failed: {str(e)}')
    
    try:
        from django.core.cache import cache
        departments = cache.get('prp_departments', [])
        dept_info = next((d for d in departments if d.get('id') == department_id), None)
        
        if dept_info:
            context['department_name'] = dept_info.get('nameEng', f'Department {department_id}')
            if hasattr(CustomUser, 'is_prp_managed'):
                existing_users = CustomUser.objects.filter(
                    office=dept_info.get('nameEng'),
                    is_prp_managed=True
                ).order_by('first_name', 'last_name')[:10]
                context['existing_users'] = existing_users
                context['existing_users_count'] = CustomUser.objects.filter(
                    office=dept_info.get('nameEng'),
                    is_prp_managed=True
                ).count()
        else:
            context['department_name'] = f'Department {department_id}'
            
    except Exception as e:
        logger.warning(f"Could not load department info: {e}")
    
    return render(request, 'users/prp_sync_department_users.html', context)


@require_http_methods(["GET"])
@login_required
@staff_member_required
def prp_sync_reports(request):
    """View to display PRP synchronization reports and analytics."""
    try:
        days_back = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days_back)
        
        total_users = CustomUser.objects.count()
        prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
        local_users = total_users - prp_users
        
        sync_stats = {}
        if hasattr(CustomUser, 'is_prp_managed'):
            never_synced = CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__isnull=True
            ).count()
            
            recently_synced = CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            needs_sync = CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__lt=timezone.now() - timedelta(days=7)
            ).count()
            
            dept_coverage = CustomUser.objects.filter(
                is_prp_managed=True
            ).values('office').annotate(
                user_count=Count('id')
            ).order_by('-user_count')[:10]
            
            recent_syncs = CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__gte=start_date
            ).order_by('-prp_last_sync')[:20]
            
            active_prp_users = CustomUser.objects.filter(
                is_prp_managed=True,
                is_active=True,
                is_active_employee=True
            ).count()
            
            sync_stats = {
                'never_synced': never_synced,
                'recently_synced': recently_synced,
                'needs_sync': needs_sync,
                'active_prp_users': active_prp_users,
                'inactive_prp_users': prp_users - active_prp_users,
                'dept_coverage': dept_coverage,
                'recent_syncs': recent_syncs,
            }
        
        api_status = {'success': False, 'error': 'Not tested'}
        try:
            prp_client = PRPClient()
            api_status = prp_client.test_connection()
        except Exception as e:
            api_status = {'success': False, 'error': str(e)}
        
        try:
            from django.core.cache import cache
            cached_departments = cache.get('prp_departments', [])
            dept_cache_time = cache.get('prp_departments_last_sync')
        except Exception:
            cached_departments = []
            dept_cache_time = None
        
        context = {
            'page_title': 'PRP Synchronization Reports',
            'breadcrumb_items': [
                {'name': 'Users', 'url': reverse('users:list')},
                {'name': 'PRP Integration', 'url': '#'},
                {'name': 'Sync Reports', 'url': ''},
            ],
            'report_period': f'Last {days_back} days',
            'report_generated': timezone.now(),
            'total_users': total_users,
            'prp_users': prp_users,
            'local_users': local_users,
            'prp_percentage': round((prp_users / total_users * 100), 1) if total_users > 0 else 0,
            'cached_departments_count': len(cached_departments),
            'dept_cache_time': dept_cache_time,
            'api_status': api_status,
            'days_options': [7, 15, 30, 60, 90],
            'selected_days': days_back,
        }
        context.update(sync_stats)
        
        return render(request, 'users/prp_sync_reports.html', context)
        
    except Exception as e:
        logger.error(f"Error generating PRP sync reports: {e}", exc_info=True)
        messages.error(request, f'Could not generate reports: {str(e)}')
        return redirect('users:list')


@require_http_methods(["GET"])
@login_required
@staff_member_required
def prp_sync_history(request):
    """View to display detailed PRP synchronization history."""
    try:
        days_back = int(request.GET.get('days', 7))
        search_query = request.GET.get('q', '').strip()
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_back)
        
        sync_activity = CustomUser.objects.none()
        if hasattr(CustomUser, 'is_prp_managed'):
            sync_activity = CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__gte=start_date,
                prp_last_sync__lte=end_date
            ).order_by('-prp_last_sync')
            
            if search_query:
                sync_activity = sync_activity.filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(employee_id__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(office__icontains=search_query)
                )
        
        paginator = Paginator(sync_activity, 20)
        page = request.GET.get('page')
        sync_records = paginator.get_page(page)
        
        total_syncs = sync_activity.count()
        unique_users = sync_activity.values('id').distinct().count()
        
        dept_breakdown = sync_activity.values('office').annotate(
            sync_count=Count('id')
        ).order_by('-sync_count')[:10]
        
        daily_activity = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            
            day_syncs = CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__gte=day_start,
                prp_last_sync__lt=day_end
            ).count()
            
            daily_activity.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'syncs': day_syncs,
                'date_formatted': current_date.strftime('%b %d')
            })
            
            current_date += timedelta(days=1)
        
        if request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="prp_sync_history_{start_date.date()}_{end_date.date()}.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Employee ID', 'Full Name', 'Email', 'Office', 
                'Last Sync Time', 'Status', 'Created At'
            ])
            
            for user in sync_activity:
                writer.writerow([
                    user.employee_id,
                    user.get_full_name(),
                    user.email,
                    user.office,
                    user.prp_last_sync.strftime('%Y-%m-%d %H:%M:%S') if user.prp_last_sync else '',
                    'Active' if user.is_active and user.is_active_employee else 'Inactive',
                    user.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            return response
        
        context = {
            'page_title': 'PRP Synchronization History',
            'breadcrumb_items': [
                {'name': 'Users', 'url': reverse('users:list')},
                {'name': 'PRP Integration', 'url': '#'},
                {'name': 'Sync History', 'url': ''},
            ],
            'sync_records': sync_records,
            'total_syncs': total_syncs,
            'unique_users': unique_users,
            'start_date': start_date,
            'end_date': end_date,
            'days_back': days_back,
            'search_query': search_query,
            'dept_breakdown': dept_breakdown,
            'daily_activity': daily_activity,
            'days_options': [1, 3, 7, 15, 30, 60, 90],
        }
        
        return render(request, 'users/prp_sync_history.html', context)
        
    except Exception as e:
        logger.error(f"Error loading PRP sync history: {e}", exc_info=True)
        messages.error(request, f'Could not load sync history: {str(e)}')
        return redirect('users:list')


@require_http_methods(["GET"])
@login_required
@staff_member_required
def prp_health_check(request):
    """Health check endpoint for PRP integration status."""
    try:
        prp_client = PRPClient()
        
        health_data = {
            'timestamp': timezone.now().isoformat(),
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'prp_base_url': settings.PRP_API_BASE_URL,
            'checks': {}
        }
        
        try:
            auth_result = prp_client.authenticate()
            health_data['checks']['authentication'] = {
                'status': 'pass' if auth_result else 'fail',
                'message': 'PRP authentication successful' if auth_result else 'PRP authentication failed'
            }
        except Exception as e:
            health_data['checks']['authentication'] = {
                'status': 'fail',
                'message': f'Authentication error: {str(e)}'
            }
        
        try:
            departments = prp_client.get_departments()
            health_data['checks']['departments_api'] = {
                'status': 'pass',
                'message': f'Retrieved {len(departments)} departments',
                'data_sample': len(departments)
            }
        except Exception as e:
            health_data['checks']['departments_api'] = {
                'status': 'fail',
                'message': f'Departments API error: {str(e)}'
            }
        
        try:
            prp_user_count = CustomUser.objects.filter(is_prp_managed=True).count()
            total_users = CustomUser.objects.count()
            
            health_data['checks']['local_data'] = {
                'status': 'pass',
                'message': f'{prp_user_count} PRP users out of {total_users} total users',
                'prp_users': prp_user_count,
                'total_users': total_users
            }
        except Exception as e:
            health_data['checks']['local_data'] = {
                'status': 'fail',
                'message': f'Local data check error: {str(e)}'
            }
        
        all_checks_passed = all(check['status'] == 'pass' for check in health_data['checks'].values())
        health_data['overall_status'] = 'healthy' if all_checks_passed else 'unhealthy'
        
        return JsonResponse(health_data)
        
    except Exception as e:
        logger.error(f"Error in PRP health check: {e}")
        return JsonResponse({
            'overall_status': 'error',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=500)


@require_POST
@login_required
@staff_member_required
def bulk_user_action(request):
    """Bulk user actions with PRP protection."""
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        action = data.get('action')
        
        if not user_ids or action not in ['activate', 'deactivate', 'delete']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid parameters'
            }, status=400)
        
        users = CustomUser.objects.filter(id__in=user_ids)
        if not users.exists():
            return JsonResponse({
                'success': False,
                'error': 'No valid users found.'
            }, status=400)
        
        if request.user.id in user_ids:
            return JsonResponse({
                'success': False,
                'error': 'You cannot perform bulk actions on your own account.'
            }, status=400)
        
        results = {
            'total_users': users.count(),
            'prp_users': 0,
            'local_users': 0,
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        with transaction.atomic():
            for user in users:
                try:
                    is_prp_user = getattr(user, 'is_prp_managed', False)
                    if is_prp_user:
                        results['prp_users'] += 1
                    else:
                        results['local_users'] += 1
                    
                    if action == 'activate':
                        if not user.is_active:
                            user.is_active = True
                            user.save(update_fields=['is_active'])
                            results['success_count'] += 1
                            
                            logger.info(
                                f"Bulk user activation: {user.username} ({user.employee_id})",
                                extra={
                                    'user_id': user.id,
                                    'activated_by': request.user.username,
                                    'is_prp_managed': is_prp_user,
                                    'bulk_operation': True,
                                    'activation_time': timezone.now().isoformat(),
                                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                                }
                            )
                    
                    elif action == 'deactivate':
                        if user.is_active:
                            user.is_active = False
                            user.save(update_fields=['is_active'])
                            results['success_count'] += 1
                            
                            logger.info(
                                f"Bulk user deactivation: {user.username} ({user.employee_id})",
                                extra={
                                    'user_id': user.id,
                                    'deactivated_by': request.user.username,
                                    'is_prp_managed': is_prp_user,
                                    'bulk_operation': True,
                                    'deactivation_time': timezone.now().isoformat(),
                                    'admin_override': is_prp_user,
                                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                                }
                            )
                    
                    elif action == 'delete':
                        if is_prp_user:
                            results['errors'].append(
                                f"Cannot delete PRP-managed user: {user.get_display_name()}"
                            )
                            results['error_count'] += 1
                        else:
                            user.delete()
                            results['success_count'] += 1
                            
                            logger.warning(
                                f"Bulk user deletion: {user.username} ({user.employee_id})",
                                extra={
                                    'user_id': user.id,
                                    'deleted_by': request.user.username,
                                    'is_prp_managed': is_prp_user,
                                    'bulk_operation': True,
                                    'deletion_time': timezone.now().isoformat(),
                                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                                }
                            )
                    
                except Exception as e:
                    results['errors'].append(f"Error processing {user.get_display_name()}: {str(e)}")
                    results['error_count'] += 1
        
        action_past_tense = {
            'activate': 'activated',
            'deactivate': 'deactivated',
            'delete': 'deleted'
        }.get(action, action)
        
        message = f"Bulk operation completed: {results['success_count']} users {action_past_tense}"
        if results['prp_users'] > 0:
            message += f" ({results['prp_users']} PRP users, {results['local_users']} local users)"
        
        return JsonResponse({
            'success': True,
            'message': message,
            'results': results
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data.'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in bulk user action: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Bulk operation failed: {str(e)}'
        }, status=500)


@login_required
@staff_member_required
def admin_prp_sync_status(request):
    """Administrative view for PRP sync status monitoring."""
    try:
        prp_client = PRPClient()
        sync_service = PRPSyncService(prp_client)
        
        status_data = {
            'api_health': sync_service.check_api_health(),
            'sync_statistics': sync_service.get_sync_statistics(),
            'recent_operations': sync_service.get_recent_operations(limit=20),
            'system_status': {
                'timestamp': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka',
                'prp_base_url': settings.PRP_API_BASE_URL
            }
        }
        
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'data': status_data
            })
        
        return render(request, 'users/admin_prp_status.html', {
            'page_title': 'PRP Integration Status',
            'status_data': status_data
        })
        
    except PRPConnectionError as e:
        logger.error(f"PRP connection error in admin status: {e}")
        error_response = {
            'success': False,
            'error': f'PRP connection failed: {str(e)}',
            'error_type': 'connection'
        }
        
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse(error_response, status=503)
        
        return render(request, 'users/admin_prp_status.html', {
            'page_title': 'PRP Integration Status',
            'connection_error': error_response
        })
    
    except Exception as e:
        logger.error(f"Unexpected error in admin PRP status: {e}")
        error_response = {
            'success': False,
            'error': str(e),
            'error_type': 'system'
        }
        
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse(error_response, status=500)
        
        return render(request, 'users/admin_prp_status.html', {
            'page_title': 'PRP Integration Status',
            'system_error': error_response
        })


# ============================================================================
# Error Handlers and Utility Functions
# ============================================================================

def handle_prp_error(error, request=None):
    """Centralized PRP error handling utility."""
    error_context = {
        'timestamp': timezone.now().isoformat(),
        'location': 'Bangladesh Parliament Secretariat, Dhaka',
        'error_type': type(error).__name__,
        'error_message': str(error)
    }
    
    if isinstance(error, PRPConnectionError):
        error_context.update({
            'user_message': 'Cannot connect to PRP system. Please try again later.',
            'admin_action': 'Check PRP API connectivity and credentials.',
            'severity': 'high'
        })
    elif isinstance(error, PRPAuthenticationError):
        error_context.update({
            'user_message': 'PRP authentication failed. Contact administrator.',
            'admin_action': 'Check PRP API credentials and token validity.',
            'severity': 'critical'
        })
    elif isinstance(error, PRPDataValidationError):
        error_context.update({
            'user_message': 'Data validation error during PRP sync.',
            'admin_action': 'Check data format and validation rules.',
            'severity': 'medium'
        })
    elif isinstance(error, PRPBusinessRuleError):
        error_context.update({
            'user_message': 'Business rule violation during PRP operation.',
            'admin_action': 'Review business rules and operation parameters.',
            'severity': 'medium'
        })
    else:
        error_context.update({
            'user_message': 'Unexpected error occurred. Contact administrator.',
            'admin_action': 'Check system logs for detailed error information.',
            'severity': 'high'
        })
    
    logger.error(
        f"PRP Integration Error: {error_context['error_type']}",
        extra=error_context
    )
    
    if request:
        messages.error(request, error_context['user_message'])
    
    return error_context


@login_required
def user_lookup_by_employee_id(request, employee_id):
    """User lookup with PRP integration."""
    try:
        try:
            user = CustomUser.objects.get(employee_id=employee_id)
            is_prp_managed = getattr(user, 'is_prp_managed', False)
            
            user_data = {
                'found': True,
                'source': 'local',
                'is_prp_managed': is_prp_managed,
                'user_id': user.id,
                'username': user.username,
                'display_name': user.get_display_name(),
                'is_active': user.is_active,
                'last_sync': getattr(user, 'prp_last_sync', None) if is_prp_managed else None
            }
            
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse(user_data)
            
            return redirect('users:detail', pk=user.id)
            
        except CustomUser.DoesNotExist:
            try:
                prp_client = PRPClient()
                prp_data = prp_client.lookup_user_by_employee_id(employee_id)
                
                if prp_data:
                    user_data = {
                        'found': True,
                        'source': 'prp',
                        'exists_locally': False,
                        'prp_data': prp_data,
                        'sync_available': True
                    }
                    
                    if request.headers.get('Accept') == 'application/json':
                        return JsonResponse(user_data)
                    
                    if request.user.is_staff:
                        messages.info(
                            request,
                            f'Employee {employee_id} found in PRP but not synced to PIMS. '
                            f'Use sync interface to import this user.'
                        )
                        return redirect('users:prp_sync_dashboard')
                    
                else:
                    user_data = {
                        'found': False,
                        'employee_id': employee_id,
                        'checked_sources': ['local', 'prp']
                    }
                    
                    if request.headers.get('Accept') == 'application/json':
                        return JsonResponse(user_data, status=404)
                    
                    messages.error(
                        request,
                        f'Employee ID {employee_id} not found in PIMS or PRP.'
                    )
                    return redirect('users:list')
                    
            except PRPConnectionError:
                user_data = {
                    'found': False,
                    'employee_id': employee_id,
                    'checked_sources': ['local', 'prp'],
                    'error': 'PRP connection failed'
                }
                
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse(user_data, status=503)
                
                messages.error(
                    request,
                    f'Employee ID {employee_id} not found. PRP connection failed.'
                )
                return redirect('users:list')
    
    except Exception as e:
        logger.error(f"Error in user lookup: {e}")
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        
        messages.error(
            request,
            f'Error looking up employee ID {employee_id}: {str(e)}'
        )
        return redirect('users:list')


@login_required
def check_prp_user_status(request):
    """AJAX endpoint to check current user's PRP status."""
    user = request.user
    
    try:
        data = {
            'is_prp_managed': getattr(user, 'is_prp_managed', False),
            'employee_id': user.employee_id,
            'last_sync': getattr(user, 'prp_last_sync', None),
            'readonly_fields': []
        }
        
        if data['is_prp_managed']:
            data['readonly_fields'] = [
                'employee_id', 'first_name', 'last_name', 'email',
                'designation', 'office', 'phone_number'
            ]
            
            if data['last_sync']:
                last_sync_dt = (
                    timezone.datetime.fromisoformat(data['last_sync'])
                    if isinstance(data['last_sync'], str)
                    else data['last_sync']
                )
                data['needs_sync'] = (timezone.now() - last_sync_dt).days > 7
        
        return JsonResponse({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error checking PRP user status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================================
# Reports and Analytics
# ============================================================================

class UserReportsView(LoginRequiredMixin, PRPAwareMixin, TemplateView):
    """User analytics and reports with PRP insights."""
    template_name = 'users/users_reports.html'
    permission_required = 'auth.view_user'
    
    def get_context_data(self, **kwargs):
        """Provide comprehensive report data with PRP analytics."""
        context = super().get_context_data(**kwargs)
        
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        staff_users = CustomUser.objects.filter(is_staff=True, is_active=True).count()
        admin_users = CustomUser.objects.filter(is_superuser=True, is_active=True).count()
        
        prp_stats = {}
        if hasattr(CustomUser, 'is_prp_managed'):
            prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
            local_users = total_users - prp_users
            prp_active = CustomUser.objects.filter(is_prp_managed=True, is_active=True).count()
            prp_inactive = prp_users - prp_active
            
            now = timezone.now()
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
            
            prp_stats = {
                'total_prp_users': prp_users,
                'local_users': local_users,
                'prp_active': prp_active,
                'prp_inactive': prp_inactive,
                'never_synced': never_synced,
                'recently_synced': recently_synced,
                'needs_sync': needs_sync,
                'sync_compliance': round((recently_synced / prp_users * 100), 1) if prp_users > 0 else 0
            }
            
            try:
                prp_client = PRPClient()
                sync_service = PRPSyncService(prp_client)
                prp_stats['api_status'] = sync_service.check_api_health()
            except Exception as e:
                logger.warning(f"Could not fetch real-time PRP statistics: {e}")
                prp_stats['api_status'] = {'connected': False, 'error': str(e)}
        
        department_stats = CustomUser.objects.values('office').annotate(
            count=Count('id'),
            prp_count=Count('id', filter=Q(is_prp_managed=True)),
            active_count=Count('id', filter=Q(is_active=True))
        ).order_by('-count')[:10]
        
        now = timezone.now()
        recent_activity = {
            'new_users_last_30_days': CustomUser.objects.filter(
                created_at__gte=now - timedelta(days=30)
            ).count(),
            'prp_syncs_last_24_hours': CustomUser.objects.filter(
                is_prp_managed=True,
                prp_last_sync__gte=now - timedelta(hours=24)
            ).count(),
        }
        
        context.update({
            'page_title': 'User Analytics & Reports - Bangladesh Parliament Secretariat',
            'basic_stats': {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'staff_users': staff_users,
                'admin_users': admin_users,
                'prp_percentage': round((prp_stats.get('total_prp_users', 0) / total_users * 100), 1) if total_users > 0 else 0
            },
            'prp_stats': prp_stats,
            'department_stats': department_stats,
            'recent_activity': recent_activity,
            'report_generated': timezone.now(),
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'days_options': [7, 15, 30, 60, 90],
            'selected_days': self.request.GET.get('days', 30)
        })

        # Add export option context
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


# ============================================================================
# Legacy View Aliases (for backward compatibility)
# ============================================================================

@method_decorator(login_required, name='dispatch')
class UserListViewLegacy(UserListView):
    """Legacy alias for UserListView."""
    pass


@method_decorator(login_required, name='dispatch')
class UserDetailViewLegacy(UserDetailView):
    """Legacy alias for UserDetailView."""
    pass


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserCreateViewLegacy(UserCreateView):
    """Legacy alias for UserCreateView."""
    pass


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserUpdateViewLegacy(UserUpdateView):
    """Legacy alias for UserUpdateView."""
    pass


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class UserDeleteViewLegacy(UserDeleteView):
    """Legacy alias for UserDeleteView."""
    pass


# ============================================================================
# Helper Functions
# ============================================================================

def get_prp_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """Helper function to fetch PRP user data with error handling."""
    try:
        prp_client = PRPClient()
        return prp_client.lookup_user_by_employee_id(user_id)
    except PRPConnectionError as e:
        logger.error(f"PRP connection error in get_prp_user_data: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_prp_user_data: {e}")
        return None


def update_user_from_prp(user: CustomUser, prp_data: Dict[str, Any]) -> bool:
    """Helper function to update user with PRP data."""
    try:
        with transaction.atomic():
            user.username = f"prp_{prp_data.get('userId')}"
            user.first_name = prp_data.get('firstName', '')
            user.last_name = prp_data.get('lastName', '')
            user.email = prp_data.get('email', '')
            user.employee_id = prp_data.get('userId', '')
            user.designation = prp_data.get('designation', '')
            user.office = prp_data.get('department', {}).get('nameEng', '')
            user.phone_number = prp_data.get('phoneNumber', '')
            user.is_prp_managed = True
            user.prp_last_sync = timezone.now()
            
            # Set default password for new PRP users
            if not user.pk:  # New user
                user.set_password("12345678")
            
            user.save()
            
            logger.info(
                f"User updated from PRP: {user.username}",
                extra={
                    'user_id': user.id,
                    'employee_id': user.employee_id,
                    'sync_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            return True
    except Exception as e:
        logger.error(f"Error updating user from PRP: {e}")
        return False


def validate_prp_data(data: Dict[str, Any]) -> bool:
    """Validate PRP data before processing."""
    required_fields = ['userId', 'firstName', 'lastName', 'email']
    return all(field in data and data[field] for field in required_fields)