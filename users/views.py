"""
Views for Users app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat, Dhaka

Enhanced with PRP (Parliament Resource Portal) Integration
This module extends existing user management views with PRP sync endpoints,
maintaining backwards compatibility while adding comprehensive PRP functionality.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Add PRP sync endpoints, user lookup APIs, and enhanced user management
"""

import json
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
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
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.safestring import mark_safe

from .models import CustomUser
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, UserRoleForm,
    UserSearchForm, UserLoginForm, PasswordResetForm
)

# Import PRP integration modules (with graceful fallback)
PRP_INTEGRATION_AVAILABLE = False
try:
    from .api.sync_service import PRPSyncService, PRPSyncResult
    from .api.prp_client import PRPClient, create_prp_client
    from .api.exceptions import (
        PRPException,
        PRPConnectionError,
        PRPAuthenticationError,
        PRPSyncError,
        PRPDataValidationError,
        PRPConfigurationError
    )
    PRP_INTEGRATION_AVAILABLE = True
except ImportError as e:
    # PRP modules not available - development mode
    PRPException = Exception
    PRPConnectionError = Exception
    PRPAuthenticationError = Exception
    PRPSyncError = Exception
    PRPDataValidationError = Exception
    PRPConfigurationError = Exception

# Configure logging
logger = logging.getLogger('pims.users.views')


# ============================================================================
# Authentication Views (ENHANCED FOR PRP)
# ============================================================================

class CustomLoginView(LoginView):
    """Enhanced custom login view supporting PRP User ID login."""
    form_class = UserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        """Handle successful login with PRP user detection."""
        user = form.cleaned_data['user']
        login(self.request, user)
        
        # Set session timeout based on remember_me
        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)  # Session expires when browser closes
        
        # Enhanced welcome message for PRP users
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            welcome_msg = f'Welcome back, {user.get_display_name()}! (PRP User)'
            # Log PRP user login for audit
            logger.info(
                f"PRP user login: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'employee_id': user.employee_id,
                    'is_prp_managed': True,
                    'login_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
        else:
            welcome_msg = f'Welcome back, {user.get_display_name()}!'
        
        messages.success(self.request, welcome_msg)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add PRP integration context to login page."""
        context = super().get_context_data(**kwargs)
        context['prp_integration_available'] = PRP_INTEGRATION_AVAILABLE
        context['location'] = 'Bangladesh Parliament Secretariat, Dhaka'
        return context


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view with PRP user handling."""
    form_class = PasswordResetForm
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')

    def form_valid(self, form):
        """Override to handle PRP users appropriately."""
        email = form.cleaned_data['email']
        
        # Check if this is a PRP user
        try:
            user = CustomUser.objects.get(email=email)
            if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
                messages.warning(
                    self.request,
                    'Note: This user is managed by Parliament Resource Portal (PRP). '
                    'Password reset will use the default PRP password.'
                )
        except CustomUser.DoesNotExist:
            pass  # User doesn't exist, let Django handle normally
        
        return super().form_valid(form)


# ============================================================================
# User CRUD Views (ENHANCED FOR PRP)
# ============================================================================

class UserListView(LoginRequiredMixin, ListView):
    """Enhanced user list view with PRP filtering and sync status."""
    model = CustomUser
    template_name = 'users/users_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        """Enhanced queryset with PRP support and filtering."""
        queryset = CustomUser.objects.select_related().annotate(
            assigned_devices_count=Count('assignment_set', distinct=True)
        )
        
        # Apply search and filtering
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
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        """Enhanced context with PRP statistics."""
        context = super().get_context_data(**kwargs)
        context['search_form'] = UserSearchForm(self.request.GET)
        context['prp_integration_available'] = PRP_INTEGRATION_AVAILABLE
        
        # Add PRP statistics if available
        if hasattr(CustomUser, 'is_prp_managed'):
            total_users = CustomUser.objects.count()
            prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
            local_users = total_users - prp_users
            
            # PRP sync statistics
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
        
        context['location'] = 'Bangladesh Parliament Secretariat, Dhaka'
        return context


class UserDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Enhanced user detail view with PRP sync information."""
    model = CustomUser
    template_name = 'users/users_detail.html'
    context_object_name = 'user_obj'
    permission_required = 'auth.view_user'
    
    def get_context_data(self, **kwargs):
        """Enhanced context with PRP sync status and assignment information."""
        context = super().get_context_data(**kwargs)
        user = self.object
        
        # Basic user information
        context['assigned_devices_count'] = user.get_assigned_devices_count()
        context['user_groups'] = user.groups.all()
        context['user_permissions'] = user.user_permissions.all()
        context['prp_integration_available'] = PRP_INTEGRATION_AVAILABLE
        
        # PRP-specific context
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            context['is_prp_user'] = True
            context['prp_sync_status'] = self._get_prp_sync_status(user)
        else:
            context['is_prp_user'] = False
        
        # Enhanced assignment context
        try:
            from assignments.models import Assignment
            
            # Get active assignments
            active_assignments = Assignment.objects.filter(
                assigned_to=user,
                is_active=True,
                status='ASSIGNED'
            ).select_related('device', 'assigned_location').order_by('-assigned_date')
            
            # Get assignment history (last 10)
            assignment_history = Assignment.objects.filter(
                assigned_to=user
            ).select_related('device', 'assigned_location').order_by('-assigned_date')[:10]
            
            # Assignment statistics
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
            # Graceful fallback if assignments app not available
            context.update({
                'active_assignments': [],
                'assignment_history': [],
                'total_assignments': 0,
                'returned_assignments': 0,
                'overdue_assignments': 0,
            })
        
        context['location'] = 'Bangladesh Parliament Secretariat, Dhaka'
        return context
    
    def _get_prp_sync_status(self, user):
        """Get detailed PRP sync status for user."""
        if not user.prp_last_sync:
            return {
                'status': 'never_synced',
                'message': 'User has never been synced from PRP',
                'last_sync': None,
                'needs_sync': True,
                'css_class': 'text-warning'
            }
        
        now = timezone.now()
        time_diff = now - user.prp_last_sync
        
        if time_diff < timedelta(hours=24):
            return {
                'status': 'recently_synced',
                'message': 'Recently synced from PRP',
                'last_sync': user.prp_last_sync,
                'needs_sync': False,
                'css_class': 'text-success'
            }
        elif time_diff < timedelta(days=7):
            return {
                'status': 'synced',
                'message': 'Synced from PRP',
                'last_sync': user.prp_last_sync,
                'needs_sync': False,
                'css_class': 'text-info'
            }
        else:
            return {
                'status': 'needs_sync',
                'message': 'Sync needed (last synced over 7 days ago)',
                'last_sync': user.prp_last_sync,
                'needs_sync': True,
                'css_class': 'text-warning'
            }


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Enhanced user creation view with PRP prevention."""
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'users/users_create.html'
    permission_required = 'auth.add_user'
    success_url = reverse_lazy('users:list')
    
    def get_context_data(self, **kwargs):
        """Add PRP context to creation form."""
        context = super().get_context_data(**kwargs)
        context['prp_integration_available'] = PRP_INTEGRATION_AVAILABLE
        context['location'] = 'Bangladesh Parliament Secretariat, Dhaka'
        return context
    
    def form_valid(self, form):
        """Enhanced form validation with PRP prevention."""
        # Additional validation to prevent PRP user creation
        if form.cleaned_data.get('is_prp_managed', False):
            form.add_error('is_prp_managed', 
                'PRP-managed users cannot be created manually. '
                'They are automatically created during PRP synchronization.'
            )
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        
        # Log local user creation
        logger.info(
            f"Local user created: {self.object.username} ({self.object.employee_id})",
            extra={
                'user_id': self.object.id,
                'created_by': self.request.user.username,
                'is_prp_managed': False,
                'creation_time': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            }
        )
        
        messages.success(
            self.request, 
            f'Local user {self.object.get_display_name()} created successfully!'
        )
        return response


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Enhanced user update view with PRP field protection."""
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'users/users_edit.html'
    permission_required = 'auth.change_user'
    
    def get_success_url(self):
        return reverse('users:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        """Add PRP context to edit form."""
        context = super().get_context_data(**kwargs)
        context['prp_integration_available'] = PRP_INTEGRATION_AVAILABLE
        context['location'] = 'Bangladesh Parliament Secretariat, Dhaka'
        
        # Add PRP user indicators
        if hasattr(self.object, 'is_prp_managed') and self.object.is_prp_managed:
            context['is_prp_user'] = True
            context['prp_sync_status'] = self._get_prp_sync_status(self.object)
        
        return context
    
    def form_valid(self, form):
        """Enhanced form validation with PRP business rules."""
        user = self.object
        
        # Log significant changes for PRP users
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
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
        
        response = super().form_valid(form)
        
        # Enhanced success message
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            messages.success(
                self.request, 
                f'PRP user {self.object.get_display_name()} updated successfully! '
                '(Some fields are managed by Parliament Resource Portal)'
            )
        else:
            messages.success(
                self.request, 
                f'Local user {self.object.get_display_name()} updated successfully!'
            )
        
        return response
    
    def _get_prp_sync_status(self, user):
        """Get PRP sync status (same as UserDetailView)."""
        if not user.prp_last_sync:
            return {
                'status': 'never_synced',
                'message': 'User has never been synced from PRP',
                'last_sync': None,
                'needs_sync': True,
                'css_class': 'text-warning'
            }
        
        now = timezone.now()
        time_diff = now - user.prp_last_sync
        
        if time_diff < timedelta(hours=24):
            return {
                'status': 'recently_synced',
                'message': 'Recently synced from PRP',
                'last_sync': user.prp_last_sync,
                'needs_sync': False,
                'css_class': 'text-success'
            }
        elif time_diff < timedelta(days=7):
            return {
                'status': 'synced',
                'message': 'Synced from PRP',
                'last_sync': user.prp_last_sync,
                'needs_sync': False,
                'css_class': 'text-info'
            }
        else:
            return {
                'status': 'needs_sync',
                'message': 'Sync needed (last synced over 7 days ago)',
                'last_sync': user.prp_last_sync,
                'needs_sync': True,
                'css_class': 'text-warning'
            }


class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Enhanced delete view with PRP user protection and self-action protection."""
    permission_required = 'auth.delete_user'
    
    def get(self, request, pk):
        """Display delete confirmation page with enhanced protection."""
        user = get_object_or_404(CustomUser, pk=pk)
        
        # PROTECTION: Prevent self-deletion
        if user.username == request.user.username:
            messages.error(
                request, 
                '⚠️ You cannot delete your own account. This would permanently remove your access.'
            )
            return redirect('users:list')
        
        # PROTECTION: Warn about PRP user deletion
        context = {
            'object': user,
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        }
        
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            context['is_prp_user'] = True
            context['prp_warning'] = (
                'This is a PRP-managed user. Deletion will remove them from PIMS, '
                'but they may be recreated during the next PRP synchronization.'
            )
        
        return render(request, 'users/users_delete.html', context)
    
    def post(self, request, pk):
        """Handle user deletion with enhanced protection."""
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # PROTECTION: Prevent self-deletion
            if user.username == request.user.username:
                messages.error(
                    request, 
                    '⚠️ You cannot delete your own account. This would permanently remove your access.'
                )
                return redirect('users:list')
            
            user_name = user.get_display_name()
            is_prp_user = hasattr(user, 'is_prp_managed') and user.is_prp_managed
            
            # Log deletion for audit
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
            
            # Enhanced success message
            if is_prp_user:
                messages.success(
                    request, 
                    f'✅ PRP user {user_name} has been deleted from PIMS! '
                    'Note: They may be recreated during the next PRP sync.'
                )
            else:
                messages.success(
                    request, 
                    f'✅ Local user {user_name} has been permanently deleted!'
                )
            
            return redirect('users:list')
            
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            messages.error(request, f'❌ Error deleting user: {str(e)}')
            return redirect('users:list')


# ============================================================================
# PRP SYNC ENDPOINTS (NEW)
# ============================================================================

@method_decorator([login_required, staff_member_required], name='dispatch')
class PRPSyncDashboardView(TemplateView):
    """PRP synchronization dashboard for admin users."""
    template_name = 'users/prp_sync_dashboard.html'
    
    def get_context_data(self, **kwargs):
        """Provide comprehensive PRP sync dashboard context."""
        context = super().get_context_data(**kwargs)
        
        if not PRP_INTEGRATION_AVAILABLE:
            context['error'] = 'PRP integration modules are not available.'
            return context
        
        try:
            # Basic statistics
            total_users = CustomUser.objects.count()
            prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
            local_users = total_users - prp_users
            
            # Sync status statistics
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
            
            # Recent sync activity
            recent_prp_users = CustomUser.objects.filter(
                is_prp_managed=True
            ).order_by('-prp_last_sync')[:10]
            
            context.update({
                'prp_integration_available': True,
                'statistics': {
                    'total_users': total_users,
                    'prp_users': prp_users,
                    'local_users': local_users,
                    'never_synced': never_synced,
                    'recently_synced': recently_synced,
                    'needs_sync': needs_sync,
                },
                'recent_prp_users': recent_prp_users,
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            })
            
        except Exception as e:
            logger.error(f"Error loading PRP sync dashboard: {e}")
            context['error'] = f'Error loading PRP sync data: {str(e)}'
        
        return context


@require_http_methods(["POST"])
@login_required
@staff_member_required  
def prp_sync_trigger(request):
    """AJAX endpoint to trigger PRP synchronization."""
    if not PRP_INTEGRATION_AVAILABLE:
        return JsonResponse({
            'success': False,
            'error': 'PRP integration is not available.'
        }, status=503)
    
    try:
        # Parse request data
        data = json.loads(request.body.decode('utf-8'))
        sync_type = data.get('sync_type', 'all')  # 'all', 'department', 'status_only'
        department_id = data.get('department_id')
        dry_run = data.get('dry_run', False)
        force = data.get('force', False)
        
        # Initialize PRP client and sync service
        try:
            prp_client = create_prp_client()
            sync_service = PRPSyncService(prp_client)
        except Exception as e:
            logger.error(f"Failed to initialize PRP client: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to connect to PRP API: {str(e)}'
            }, status=500)
        
        # Execute sync based on type
        with transaction.atomic():
            if sync_type == 'all':
                result = sync_service.sync_all_departments(
                    dry_run=dry_run,
                    force=force
                )
            elif sync_type == 'department' and department_id:
                result = sync_service.sync_department_users(
                    department_id=int(department_id),
                    dry_run=dry_run,
                    force=force
                )
            elif sync_type == 'status_only':
                result = sync_service.sync_user_status_only(
                    dry_run=dry_run,
                    force=force
                )
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid sync type specified.'
                }, status=400)
        
        # Log sync operation
        logger.info(
            f"PRP sync triggered by {request.user.username}: {sync_type}",
            extra={
                'sync_type': sync_type,
                'department_id': department_id,
                'dry_run': dry_run,
                'force': force,
                'triggered_by': request.user.username,
                'result_summary': {
                    'users_created': result.users_created,
                    'users_updated': result.users_updated,
                    'errors': result.errors
                },
                'sync_time': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            }
        )
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'PRP synchronization completed successfully!',
            'result': {
                'users_created': result.users_created,
                'users_updated': result.users_updated,
                'users_unchanged': result.users_unchanged,
                'errors': result.errors,
                'departments_processed': getattr(result, 'departments_processed', 1),
                'dry_run': dry_run,
                'sync_type': sync_type,
                'sync_time': timezone.now().isoformat()
            }
        })
        
    except PRPConnectionError as e:
        logger.error(f"PRP connection error during sync: {e}")
        return JsonResponse({
            'success': False,
            'error': f'PRP connection failed: {str(e)}. Please check network connectivity and API status.'
        }, status=503)
        
    except PRPAuthenticationError as e:
        logger.error(f"PRP authentication error during sync: {e}")
        return JsonResponse({
            'success': False,
            'error': f'PRP authentication failed: {str(e)}. Please check API credentials.'
        }, status=401)
        
    except PRPSyncError as e:
        logger.error(f"PRP sync error: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Synchronization failed: {str(e)}'
        }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data in request.'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Unexpected error during PRP sync: {e}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error occurred: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
@login_required
@staff_member_required
def prp_departments_api(request):
    """AJAX endpoint to get PRP departments list."""
    if not PRP_INTEGRATION_AVAILABLE:
        return JsonResponse({
            'success': False,
            'error': 'PRP integration is not available.'
        }, status=503)
    
    try:
        # Initialize PRP client
        prp_client = create_prp_client()
        sync_service = PRPSyncService(prp_client)
        
        # Get departments from PRP
        departments = sync_service.get_prp_departments()
        
        # Format for frontend
        formatted_departments = [
            {
                'id': dept['id'],
                'nameEng': dept.get('nameEng', f"Department {dept['id']}"),
                'nameBng': dept.get('nameBng', ''),
                'isWing': dept.get('isWing', False)
            }
            for dept in departments
        ]
        
        return JsonResponse({
            'success': True,
            'departments': formatted_departments,
            'count': len(formatted_departments)
        })
        
    except PRPConnectionError as e:
        logger.error(f"PRP connection error getting departments: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to connect to PRP API: {str(e)}'
        }, status=503)
        
    except Exception as e:
        logger.error(f"Error getting PRP departments: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error retrieving departments: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
@login_required
def prp_user_lookup(request, employee_id):
    """AJAX endpoint for PRP user lookup by employee ID."""
    if not PRP_INTEGRATION_AVAILABLE:
        return JsonResponse({
            'success': False,
            'error': 'PRP integration is not available.'
        }, status=503)
    
    try:
        # Look up user in PIMS first
        try:
            local_user = CustomUser.objects.get(employee_id=employee_id)
            user_data = {
                'found_in_pims': True,
                'user_id': local_user.id,
                'username': local_user.username,
                'full_name': local_user.get_full_name(),
                'email': local_user.email,
                'designation': local_user.designation,
                'office': local_user.office,
                'is_prp_managed': getattr(local_user, 'is_prp_managed', False),
                'is_active': local_user.is_active,
                'last_sync': getattr(local_user, 'prp_last_sync', None),
                'profile_url': reverse('users:detail', kwargs={'pk': local_user.pk})
            }
            
            if user_data['last_sync']:
                user_data['last_sync'] = user_data['last_sync'].isoformat()
                
        except CustomUser.DoesNotExist:
            user_data = {'found_in_pims': False}
        
        # Look up user in PRP
        try:
            prp_client = create_prp_client()
            sync_service = PRPSyncService(prp_client)
            
            prp_user_data = sync_service.lookup_user_by_employee_id(employee_id)
            
            if prp_user_data:
                user_data.update({
                    'found_in_prp': True,
                    'prp_data': {
                        'userId': prp_user_data.get('userId'),
                        'nameEng': prp_user_data.get('nameEng'),
                        'email': prp_user_data.get('email'),
                        'designation': prp_user_data.get('designationEng'),
                        'mobile': prp_user_data.get('mobile'),
                        'status': prp_user_data.get('status'),
                        'departmentId': prp_user_data.get('departmentId')
                    }
                })
            else:
                user_data['found_in_prp'] = False
                
        except Exception as e:
            logger.warning(f"PRP lookup failed for employee {employee_id}: {e}")
            user_data['found_in_prp'] = False
            user_data['prp_error'] = str(e)
        
        return JsonResponse({
            'success': True,
            'employee_id': employee_id,
            **user_data
        })
        
    except Exception as e:
        logger.error(f"Error in PRP user lookup: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Lookup failed: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
@login_required
@staff_member_required
def prp_sync_status(request):
    """AJAX endpoint to get current PRP sync status."""
    if not PRP_INTEGRATION_AVAILABLE:
        return JsonResponse({
            'success': False,
            'error': 'PRP integration is not available.'
        }, status=503)
    
    try:
        # Get basic sync statistics
        now = timezone.now()
        total_users = CustomUser.objects.count()
        prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
        
        # Detailed sync status
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
        
        # Last sync information
        last_synced_user = CustomUser.objects.filter(
            is_prp_managed=True,
            prp_last_sync__isnull=False
        ).order_by('-prp_last_sync').first()
        
        # Test PRP API connection
        try:
            prp_client = create_prp_client()
            connection_test = prp_client.test_connection()
            api_status = 'connected' if connection_test['success'] else 'failed'
            api_error = connection_test.get('error')
        except Exception as e:
            api_status = 'error'
            api_error = str(e)
        
        return JsonResponse({
            'success': True,
            'sync_status': {
                'total_users': total_users,
                'prp_users': prp_users,
                'local_users': total_users - prp_users,
                'never_synced': never_synced,
                'recently_synced': recently_synced,
                'needs_sync': needs_sync,
                'last_sync_time': last_synced_user.prp_last_sync.isoformat() if last_synced_user and last_synced_user.prp_last_sync else None,
                'last_synced_user': last_synced_user.get_display_name() if last_synced_user else None,
                'api_status': api_status,
                'api_error': api_error,
                'check_time': now.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting PRP sync status: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Status check failed: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@login_required
@staff_member_required
def prp_sync_single_user(request, pk):
    """AJAX endpoint to sync a single user from PRP."""
    if not PRP_INTEGRATION_AVAILABLE:
        return JsonResponse({
            'success': False,
            'error': 'PRP integration is not available.'
        }, status=503)
    
    try:
        user = get_object_or_404(CustomUser, pk=pk)
        
        # Verify this is a PRP user
        if not getattr(user, 'is_prp_managed', False):
            return JsonResponse({
                'success': False,
                'error': 'This is not a PRP-managed user.'
            }, status=400)
        
        # Parse request options
        try:
            data = json.loads(request.body.decode('utf-8'))
            force = data.get('force', False)
        except json.JSONDecodeError:
            force = False
        
        # Initialize sync service
        prp_client = create_prp_client()
        sync_service = PRPSyncService(prp_client)
        
        # Sync single user
        with transaction.atomic():
            result = sync_service.sync_single_user(
                employee_id=user.employee_id,
                force=force
            )
        
        # Log operation
        logger.info(
            f"Single PRP user sync: {user.username} ({user.employee_id})",
            extra={
                'user_id': user.id,
                'synced_by': request.user.username,
                'force': force,
                'sync_time': timezone.now().isoformat(),
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'User {user.get_display_name()} synced successfully!',
            'result': {
                'user_updated': result.users_updated > 0,
                'user_created': result.users_created > 0,
                'errors': result.errors,
                'sync_time': timezone.now().isoformat()
            }
        })
        
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found.'
        }, status=404)
        
    except PRPException as e:
        logger.error(f"PRP error syncing single user: {e}")
        return JsonResponse({
            'success': False,
            'error': f'PRP sync failed: {str(e)}'
        }, status=500)
        
    except Exception as e:
        logger.error(f"Error syncing single user: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Sync failed: {str(e)}'
        }, status=500)


# ============================================================================
# User Role and Permission Management (ENHANCED FOR PRP)
# ============================================================================

class UserRoleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Enhanced user roles update with PRP user handling."""
    model = CustomUser
    form_class = UserRoleForm
    template_name = 'users/users_roles.html'
    permission_required = 'auth.change_user'
    
    def get_success_url(self):
        return reverse('users:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        """Add PRP context to roles form."""
        context = super().get_context_data(**kwargs)
        context['prp_integration_available'] = PRP_INTEGRATION_AVAILABLE
        context['location'] = 'Bangladesh Parliament Secretariat, Dhaka'
        
        if hasattr(self.object, 'is_prp_managed') and self.object.is_prp_managed:
            context['is_prp_user'] = True
            context['prp_note'] = (
                'This user is managed by Parliament Resource Portal (PRP). '
                'Role assignments are preserved during PRP synchronization.'
            )
        
        return context
    
    def form_valid(self, form):
        """Handle successful role assignment with PRP logging."""
        user = self.object
        
        # Log role changes for PRP users
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            logger.info(
                f"PRP user roles updated: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'modified_by': self.request.user.username,
                    'is_prp_managed': True,
                    'modification_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
        
        response = super().form_valid(form)
        
        # Enhanced success message
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            messages.success(
                self.request, 
                f'Roles updated for PRP user {self.object.get_display_name()}! '
                'Role assignments are preserved during sync.'
            )
        else:
            messages.success(
                self.request, 
                f'Roles updated for {self.object.get_display_name()}!'
            )
        
        return response


class UserPermissionView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Enhanced user permissions view with PRP context."""
    model = CustomUser
    template_name = 'users/users_permissions.html'
    permission_required = 'auth.view_user'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        """Enhanced permission context with PRP information."""
        context = super().get_context_data(**kwargs)
        user = self.object
        
        # Get all permissions (direct and through groups)
        all_permissions = user.get_all_permissions()
        group_permissions = user.get_group_permissions()
        direct_permissions = user.user_permissions.all()
        
        context.update({
            'all_permissions': sorted(all_permissions),
            'group_permissions': sorted(group_permissions),
            'direct_permissions': direct_permissions,
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        })
        
        # Add PRP context
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            context['is_prp_user'] = True
            context['prp_note'] = (
                'This user is managed by Parliament Resource Portal (PRP). '
                'Permissions are managed locally and preserved during sync.'
            )
        
        return context


# ============================================================================
# User Profile Management (ENHANCED FOR PRP)
# ============================================================================

class UserProfileView(LoginRequiredMixin, DetailView):
    """Enhanced user profile view with PRP status."""
    model = CustomUser
    template_name = 'users/users_profile.html'
    context_object_name = 'user_obj'
    
    def get_object(self):
        """Return current user."""
        return self.request.user
    
    def get_context_data(self, **kwargs):
        """Enhanced profile context with PRP information."""
        context = super().get_context_data(**kwargs)
        user = self.object
        
        context.update({
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        })
        
        # Add PRP-specific context
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            context['is_prp_user'] = True
            context['prp_sync_status'] = self._get_prp_sync_status(user)
            context['prp_profile_note'] = (
                'Your profile is managed by Parliament Resource Portal (PRP). '
                'Some information is automatically synchronized and cannot be edited.'
            )
        
        return context
    
    def _get_prp_sync_status(self, user):
        """Get PRP sync status for profile view."""
        if not hasattr(user, 'prp_last_sync') or not user.prp_last_sync:
            return {
                'status': 'never_synced',
                'message': 'Profile has never been synced from PRP',
                'css_class': 'text-warning'
            }
        
        now = timezone.now()
        time_diff = now - user.prp_last_sync
        
        if time_diff < timedelta(hours=24):
            return {
                'status': 'recently_synced',
                'message': 'Profile recently synced from PRP',
                'last_sync': user.prp_last_sync,
                'css_class': 'text-success'
            }
        elif time_diff < timedelta(days=7):
            return {
                'status': 'synced',
                'message': 'Profile synced from PRP',
                'last_sync': user.prp_last_sync,
                'css_class': 'text-info'
            }
        else:
            return {
                'status': 'needs_sync',
                'message': 'Profile sync needed',
                'last_sync': user.prp_last_sync,
                'css_class': 'text-warning'
            }


class UserProfileEditView(LoginRequiredMixin, UpdateView):
    """Enhanced profile edit view with PRP field protection."""
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'users/users_profile_edit.html'
    success_url = reverse_lazy('users:profile')
    
    def get_object(self):
        """Return current user."""
        return self.request.user
    
    def get_context_data(self, **kwargs):
        """Enhanced profile edit context with PRP information."""
        context = super().get_context_data(**kwargs)
        user = self.object
        
        context.update({
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        })
        
        # Add PRP context
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            context['is_prp_user'] = True
            context['prp_edit_note'] = (
                'Some fields are managed by Parliament Resource Portal (PRP) '
                'and cannot be edited. Changes to editable fields will be preserved.'
            )
        
        return context
    
    def form_valid(self, form):
        """Handle successful profile update with PRP considerations."""
        user = self.object
        
        # Log profile changes for PRP users
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            logger.info(
                f"PRP user profile updated: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'self_modified': True,
                    'is_prp_managed': True,
                    'modification_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
        
        response = super().form_valid(form)
        
        # Enhanced success message
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            messages.success(
                self.request, 
                'Your profile has been updated! PRP-managed fields remain protected.'
            )
        else:
            messages.success(
                self.request, 
                'Your profile has been updated successfully!'
            )
        
        return response


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Enhanced password change view with PRP user handling."""
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('users:profile')
    
    def get_context_data(self, **kwargs):
        """Add PRP context to password change form."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context.update({
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        })
        
        # Add PRP warning
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            context['is_prp_user'] = True
            context['prp_password_note'] = (
                'You are a PRP-managed user. Password changes will be preserved, '
                'but the default PRP password (12345678) can always be used for login.'
            )
        
        return context
    
    def form_valid(self, form):
        """Handle successful password change with PRP logging."""
        user = self.request.user
        
        # Log password changes for PRP users
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            logger.info(
                f"PRP user password changed: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'self_modified': True,
                    'is_prp_managed': True,
                    'modification_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
        
        response = super().form_valid(form)
        
        # Enhanced success message
        if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
            messages.success(
                self.request, 
                'Your password has been changed! You can still use the default PRP password (12345678) to login.'
            )
        else:
            messages.success(
                self.request, 
                'Your password has been changed successfully!'
            )
        
        return response


# ============================================================================
# User Search and Filtering (ENHANCED FOR PRP)
# ============================================================================

class UserSearchView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Enhanced user search view with comprehensive PRP filtering."""
    model = CustomUser
    template_name = 'users/users_search.html'
    context_object_name = 'users'
    paginate_by = 15
    permission_required = 'auth.view_user'
    
    def get_queryset(self):
        """Enhanced search queryset with PRP support."""
        queryset = CustomUser.objects.select_related().annotate(
            assigned_devices_count=Count('assignment_set', distinct=True)
        )
        
        # Apply advanced search filters
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
            
            # Multi-field search
            if search:
                queryset = queryset.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(username__icontains=search) |
                    Q(email__icontains=search) |
                    Q(employee_id__icontains=search) |
                    Q(designation__icontains=search) |
                    Q(office__icontains=search)
                )
            
            # Specific field filters
            if office:
                queryset = queryset.filter(office__icontains=office)
            if designation:
                queryset = queryset.filter(designation__icontains=designation)
            if group:
                queryset = queryset.filter(groups=group)
            if is_active:
                queryset = queryset.filter(is_active=(is_active == 'true'))
            if is_staff:
                queryset = queryset.filter(is_staff=(is_staff == 'true'))
            
            # PRP-specific filters
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
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        """Enhanced search context with PRP statistics."""
        context = super().get_context_data(**kwargs)
        context['search_form'] = UserSearchForm(self.request.GET)
        context['prp_integration_available'] = PRP_INTEGRATION_AVAILABLE
        context['location'] = 'Bangladesh Parliament Secretariat, Dhaka'
        
        # Search result statistics
        if self.object_list:
            total_results = self.object_list.count() if hasattr(self.object_list, 'count') else len(self.object_list)
            
            if hasattr(CustomUser, 'is_prp_managed'):
                prp_results = sum(1 for user in self.object_list if getattr(user, 'is_prp_managed', False))
                local_results = total_results - prp_results
                
                context['search_stats'] = {
                    'total_results': total_results,
                    'prp_results': prp_results,
                    'local_results': local_results
                }
        
        return context


# ============================================================================
# AJAX Employee ID Lookup (ENHANCED FOR PRP)
# ============================================================================

@require_http_methods(["GET"])
@login_required
def user_lookup_by_employee_id(request, employee_id):
    """Enhanced AJAX endpoint for employee ID lookup with PRP support."""
    try:
        # Look up user in PIMS
        try:
            user = CustomUser.objects.get(employee_id=employee_id)
            user_data = {
                'found': True,
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'display_name': user.get_display_name(),
                'email': user.email,
                'designation': user.designation,
                'office': user.office,
                'phone_number': user.phone_number,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_prp_managed': getattr(user, 'is_prp_managed', False),
                'date_joined': user.date_joined.isoformat(),
                'profile_url': reverse('users:detail', kwargs={'pk': user.pk}),
                'edit_url': reverse('users:edit', kwargs={'pk': user.pk})
            }
            
            # Add PRP-specific data
            if getattr(user, 'is_prp_managed', False):
                user_data['prp_last_sync'] = getattr(user, 'prp_last_sync', None)
                if user_data['prp_last_sync']:
                    user_data['prp_last_sync'] = user_data['prp_last_sync'].isoformat()
                
                # Add sync status
                user_data['prp_sync_status'] = 'never_synced'
                if user_data['prp_last_sync']:
                    now = timezone.now()
                    last_sync = timezone.datetime.fromisoformat(user_data['prp_last_sync'].replace('Z', '+00:00'))
                    time_diff = now - last_sync
                    
                    if time_diff < timedelta(hours=24):
                        user_data['prp_sync_status'] = 'recently_synced'
                    elif time_diff < timedelta(days=7):
                        user_data['prp_sync_status'] = 'synced'
                    else:
                        user_data['prp_sync_status'] = 'needs_sync'
            
            # Add assignment information
            try:
                from assignments.models import Assignment
                active_assignments = Assignment.objects.filter(
                    assigned_to=user,
                    is_active=True,
                    status='ASSIGNED'
                ).count()
                user_data['active_assignments'] = active_assignments
            except ImportError:
                user_data['active_assignments'] = 0
                
        except CustomUser.DoesNotExist:
            user_data = {'found': False}
        
        return JsonResponse({
            'success': True,
            'employee_id': employee_id,
            **user_data
        })
        
    except Exception as e:
        logger.error(f"Error in user lookup by employee ID: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Lookup failed: {str(e)}'
        }, status=500)


# ============================================================================
# User Status Management (ENHANCED FOR PRP)
# ============================================================================

@method_decorator([login_required, staff_member_required], name='dispatch')
class UserActivateView(View):
    """Enhanced user activation view with PRP business rules."""
    
    def post(self, request, pk):
        """Activate user with PRP considerations."""
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # Prevent self-modification of active status
            if user.pk == request.user.pk:
                return JsonResponse({
                    'success': False,
                    'error': 'You cannot modify your own active status.'
                }, status=400)
            
            user.is_active = True
            user.save(update_fields=['is_active'])
            
            # Log activation
            logger.info(
                f"User activated: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'activated_by': request.user.username,
                    'is_prp_managed': getattr(user, 'is_prp_managed', False),
                    'activation_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            
            # Enhanced success message for PRP users
            if getattr(user, 'is_prp_managed', False):
                message = f'PRP user {user.get_display_name()} has been activated! This override will be preserved during PRP sync.'
            else:
                message = f'User {user.get_display_name()} has been activated!'
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'user_status': 'active'
                })
            else:
                messages.success(request, message)
                return redirect('users:detail', pk=pk)
                
        except Exception as e:
            logger.error(f"Error activating user: {e}")
            error_msg = f'Failed to activate user: {str(e)}'
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=500)
            else:
                messages.error(request, error_msg)
                return redirect('users:list')


@method_decorator([login_required, staff_member_required], name='dispatch')
class UserDeactivateView(View):
    """Enhanced user deactivation view with PRP business rules."""
    
    def post(self, request, pk):
        """Deactivate user with PRP considerations."""
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # Prevent self-deactivation
            if user.pk == request.user.pk:
                return JsonResponse({
                    'success': False,
                    'error': 'You cannot deactivate your own account.'
                }, status=400)
            
            # Prevent deactivating superusers
            if user.is_superuser:
                return JsonResponse({
                    'success': False,
                    'error': 'Superuser accounts cannot be deactivated.'
                }, status=400)
            
            user.is_active = False
            user.save(update_fields=['is_active'])
            
            # Log deactivation
            logger.info(
                f"User deactivated: {user.username} ({user.employee_id})",
                extra={
                    'user_id': user.id,
                    'deactivated_by': request.user.username,
                    'is_prp_managed': getattr(user, 'is_prp_managed', False),
                    'deactivation_time': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka'
                }
            )
            
            # Enhanced success message for PRP users
            if getattr(user, 'is_prp_managed', False):
                message = f'PRP user {user.get_display_name()} has been deactivated! This override will be preserved during PRP sync.'
            else:
                message = f'User {user.get_display_name()} has been deactivated!'
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'user_status': 'inactive'
                })
            else:
                messages.success(request, message)
                return redirect('users:detail', pk=pk)
                
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            error_msg = f'Failed to deactivate user: {str(e)}'
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=500)
            else:
                messages.error(request, error_msg)
                return redirect('users:list')


# ============================================================================
# Bulk Operations (ENHANCED FOR PRP)
# ============================================================================

@require_http_methods(["POST"])
@login_required
@staff_member_required
def bulk_user_action(request):
    """Enhanced bulk user operations with PRP awareness."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        action = data.get('action')
        user_ids = data.get('user_ids', [])
        
        if not action or not user_ids:
            return JsonResponse({
                'success': False,
                'error': 'Action and user IDs are required.'
            }, status=400)
        
        # Get users
        users = CustomUser.objects.filter(id__in=user_ids)
        if not users.exists():
            return JsonResponse({
                'success': False,
                'error': 'No valid users found.'
            }, status=400)
        
        # Prevent self-modification in bulk actions
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
                            
                            # Log activation
                            logger.info(
                                f"Bulk user activation: {user.username} ({user.employee_id})",
                                extra={
                                    'user_id': user.id,
                                    'activated_by': request.user.username,
                                    'is_prp_managed': is_prp_user,
                                    'bulk_operation': True,
                                    'activation_time': timezone.now().isoformat()
                                }
                            )
                    
                    elif action == 'deactivate':
                        if user.is_active and not user.is_superuser:
                            user.is_active = False
                            user.save(update_fields=['is_active'])
                            results['success_count'] += 1
                            
                            # Log deactivation
                            logger.info(
                                f"Bulk user deactivation: {user.username} ({user.employee_id})",
                                extra={
                                    'user_id': user.id,
                                    'deactivated_by': request.user.username,
                                    'is_prp_managed': is_prp_user,
                                    'bulk_operation': True,
                                    'deactivation_time': timezone.now().isoformat()
                                }
                            )
                        elif user.is_superuser:
                            results['errors'].append(f"Cannot deactivate superuser: {user.get_display_name()}")
                            results['error_count'] += 1
                    
                    elif action == 'delete' and not user.is_superuser:
                        user_name = user.get_display_name()
                        user.delete()
                        results['success_count'] += 1
                        
                        # Log deletion
                        logger.warning(
                            f"Bulk user deletion: {user.username} ({user.employee_id})",
                            extra={
                                'user_id': user.id,
                                'deleted_by': request.user.username,
                                'is_prp_managed': is_prp_user,
                                'bulk_operation': True,
                                'deletion_time': timezone.now().isoformat()
                            }
                        )
                    
                    else:
                        results['errors'].append(f"Invalid action or protected user: {user.get_display_name()}")
                        results['error_count'] += 1
                        
                except Exception as e:
                    results['errors'].append(f"Error processing {user.get_display_name()}: {str(e)}")
                    results['error_count'] += 1
        
        # Generate success message
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


# ============================================================================
# Reports and Analytics (ENHANCED FOR PRP)
# ============================================================================

class UserReportsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Enhanced user analytics and reports with PRP insights."""
    template_name = 'users/users_reports.html'
    permission_required = 'auth.view_user'
    
    def get_context_data(self, **kwargs):
        """Enhanced report data with comprehensive PRP analytics."""
        context = super().get_context_data(**kwargs)
        
        # Basic user statistics
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        staff_users = CustomUser.objects.filter(is_staff=True, is_active=True).count()
        admin_users = CustomUser.objects.filter(is_superuser=True, is_active=True).count()
        
        # PRP-specific statistics
        prp_stats = {}
        if hasattr(CustomUser, 'is_prp_managed'):
            prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
            local_users = total_users - prp_users
            prp_active = CustomUser.objects.filter(is_prp_managed=True, is_active=True).count()
            prp_inactive = prp_users - prp_active
            
            # Sync statistics
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
            
            # Department breakdown for PRP users
            prp_departments = CustomUser.objects.filter(
                is_prp_managed=True
            ).values('office').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            prp_stats = {
                'total_prp_users': prp_users,
                'total_local_users': local_users,
                'prp_active': prp_active,
                'prp_inactive': prp_inactive,
                'never_synced': never_synced,
                'recently_synced': recently_synced,
                'needs_sync': needs_sync,
                'top_departments': list(prp_departments)
            }
        
        # Role distribution
        role_distribution = Group.objects.annotate(
            user_count=Count('user')
        ).order_by('-user_count')
        
        # Recent activity
        recent_users = CustomUser.objects.order_by('-date_joined')[:10]
        
        # Device assignment statistics (if available)
        assignment_stats = {}
        try:
            from assignments.models import Assignment
            total_assignments = Assignment.objects.count()
            active_assignments = Assignment.objects.filter(
                is_active=True,
                status='ASSIGNED'
            ).count()
            
            # Top users by assignments
            top_assigned_users = CustomUser.objects.annotate(
                assignment_count=Count('assignment_set')
            ).filter(
                assignment_count__gt=0
            ).order_by('-assignment_count')[:10]
            
            assignment_stats = {
                'total_assignments': total_assignments,
                'active_assignments': active_assignments,
                'top_assigned_users': top_assigned_users
            }
        except ImportError:
            pass
        
        context.update({
            'statistics': {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'staff_users': staff_users,
                'admin_users': admin_users,
                'activation_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0
            },
            'prp_stats': prp_stats,
            'role_distribution': role_distribution,
            'recent_users': recent_users,
            'assignment_stats': assignment_stats,
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'location': 'Bangladesh Parliament Secretariat, Dhaka'
        })
        
        return context


@require_http_methods(["GET"])
@login_required
@staff_member_required
def user_export(request):
    """Enhanced user export with PRP data included."""
    try:
        export_format = request.GET.get('format', 'csv')
        include_prp_data = request.GET.get('include_prp', 'true').lower() == 'true'
        
        # Get users queryset
        users = CustomUser.objects.select_related().order_by('employee_id')
        
        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="pims_users_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            import csv
            writer = csv.writer(response)
            
            # CSV Headers
            headers = [
                'Employee ID', 'Username', 'First Name', 'Last Name', 'Full Name',
                'Email', 'Designation', 'Office', 'Phone', 'Is Active', 'Is Staff',
                'Date Joined', 'Last Login'
            ]
            
            if include_prp_data and hasattr(CustomUser, 'is_prp_managed'):
                headers.extend([
                    'Is PRP Managed', 'PRP Last Sync', 'PRP Sync Status'
                ])
            
            writer.writerow(headers)
            
            # CSV Data
            for user in users:
                row = [
                    user.employee_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.get_full_name(),
                    user.email,
                    user.designation,
                    user.office,
                    user.phone_number,
                    'Yes' if user.is_active else 'No',
                    'Yes' if user.is_staff else 'No',
                    user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if user.date_joined else '',
                    user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
                ]
                
                if include_prp_data and hasattr(user, 'is_prp_managed'):
                    is_prp = getattr(user, 'is_prp_managed', False)
                    prp_sync = getattr(user, 'prp_last_sync', None)
                    
                    row.extend([
                        'Yes' if is_prp else 'No',
                        prp_sync.strftime('%Y-%m-%d %H:%M:%S') if prp_sync else 'Never',
                        get_prp_sync_status_text(user, prp_sync) if is_prp else 'N/A'
                    ])
                
                writer.writerow(row)
            
            return response
            
        else:
            return JsonResponse({
                'success': False,
                'error': 'Unsupported export format. Only CSV is currently supported.'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error exporting users: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Export failed: {str(e)}'
        }, status=500)


def get_prp_sync_status_text(user, prp_sync):
    """Helper function to get PRP sync status text for export."""
    if not prp_sync:
        return 'Never Synced'
    
    now = timezone.now()
    time_diff = now - prp_sync
    
    if time_diff < timedelta(hours=24):
        return 'Recently Synced'
    elif time_diff < timedelta(days=7):
        return 'Synced'
    else:
        return 'Needs Sync'


# ============================================================================
# Status Checking Utilities (ENHANCED FOR PRP)
# ============================================================================

def get_user_status_summary():
    """
    Enhanced user status summary with PRP integration data.
    Returns comprehensive dictionary with counts and PRP statistics.
    """
    try:
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        staff_users = CustomUser.objects.filter(is_staff=True, is_active=True).count()
        admin_users = CustomUser.objects.filter(is_superuser=True, is_active=True).count()
        
        summary = {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'staff_users': staff_users,
            'admin_users': admin_users,
            'activation_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0,
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE
        }
        
        # Add PRP statistics if available
        if hasattr(CustomUser, 'is_prp_managed'):
            prp_users = CustomUser.objects.filter(is_prp_managed=True).count()
            local_users = total_users - prp_users
            
            # PRP sync statistics
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
            
            summary.update({
                'prp_users': prp_users,
                'local_users': local_users,
                'prp_never_synced': never_synced,
                'prp_recently_synced': recently_synced,
                'prp_needs_sync': needs_sync,
                'prp_sync_rate': round(((prp_users - never_synced) / prp_users * 100), 2) if prp_users > 0 else 0
            })
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting user status summary: {e}")
        return {
            'total_users': 0,
            'active_users': 0,
            'inactive_users': 0,
            'staff_users': 0,
            'admin_users': 0,
            'activation_rate': 0,
            'prp_integration_available': PRP_INTEGRATION_AVAILABLE,
            'error': str(e)
        }


# ============================================================================
# BACKWARDS COMPATIBILITY FUNCTIONS
# ============================================================================

# Maintain backwards compatibility with existing code
def user_lookup_by_employee_id_legacy(request, employee_id):
    """Legacy function name - redirects to new implementation."""
    return user_lookup_by_employee_id(request, employee_id)


# Legacy view aliases for backwards compatibility
UserList = UserListView
UserDetail = UserDetailView  
UserCreate = UserCreateView
UserUpdate = UserUpdateView
UserDelete = UserDeleteView