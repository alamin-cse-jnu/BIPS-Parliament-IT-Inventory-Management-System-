

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
)
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .models import CustomUser
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, UserRoleForm,
    UserSearchForm, UserLoginForm, PasswordResetForm
)


# ============================================================================
# Authentication Views
# ============================================================================

class CustomLoginView(LoginView):
    """Custom login view supporting username or employee ID."""
    form_class = UserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        """Handle successful login."""
        user = form.cleaned_data['user']
        login(self.request, user)
        
        # Set session timeout based on remember_me
        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)  # Session expires when browser closes
        
        messages.success(self.request, f'Welcome back, {user.get_display_name()}!')
        return super().form_valid(form)


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view."""
    form_class = PasswordResetForm
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')


# ============================================================================
# User CRUD Views
# ============================================================================

class UserListView(LoginRequiredMixin, ListView):
    """Display list of all users with search and filtering."""
    model = CustomUser
    template_name = 'users/users_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter users based on search parameters."""
        queryset = CustomUser.objects.select_related().prefetch_related('groups')
        
        # Get search parameters from the form
        search = self.request.GET.get('search')
        department = self.request.GET.get('department') 
        status = self.request.GET.get('status')          
        role = self.request.GET.get('role')              
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Apply department filter (using office field)
        if department:
            queryset = queryset.filter(office__icontains=department)
            
        # Apply status filter
        if status == 'active':
            queryset = queryset.filter(is_active=True, is_active_employee=True)
        elif status == 'inactive':
            queryset = queryset.filter(Q(is_active=False) | Q(is_active_employee=False))
            
        # Apply role filter
        if role == 'superuser':
            queryset = queryset.filter(is_superuser=True)
        elif role == 'staff':
            queryset = queryset.filter(is_staff=True, is_superuser=False)
        elif role == 'user':
            queryset = queryset.filter(is_staff=False, is_superuser=False)
        
        return queryset.order_by('employee_id', 'last_name')
    
    def get_context_data(self, **kwargs):
        """Add search form to context."""
        context = super().get_context_data(**kwargs)
        context['search_form'] = UserSearchForm(self.request.GET)
        context['total_users'] = CustomUser.objects.count()
        context['active_users'] = CustomUser.get_active_employees().count()
        
        # Add current filter values for form persistence
        context['current_search'] = self.request.GET.get('search', '')
        context['current_department'] = self.request.GET.get('department', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_role'] = self.request.GET.get('role', '')
        
        return context


class UserDetailView(LoginRequiredMixin, DetailView):
    """Display detailed information about a user."""
    model = CustomUser
    template_name = 'users/users_detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        user = self.object
        context['assigned_devices_count'] = user.get_assigned_devices_count()
        context['user_groups'] = user.groups.all()
        context['user_permissions'] = user.user_permissions.all()
        return context


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a new user."""
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'users/users_create.html'
    permission_required = 'auth.add_user'
    success_url = reverse_lazy('users:list')
    
    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'User {self.object.get_display_name()} created successfully!'
        )
        return response


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update an existing user."""
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'users/users_edit.html'
    permission_required = 'auth.change_user'
    
    def get_success_url(self):
        return reverse('users:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'User {self.object.get_display_name()} updated successfully!'
        )
        return response


class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Delete view with self-action protection.
    Location: Dhaka, Bangladesh - Parliament IT Management System
    """
    permission_required = 'auth.delete_user'
    
    def get(self, request, pk):
        """Display delete confirmation page with protection."""
        user = get_object_or_404(CustomUser, pk=pk)
        
        # BACKEND PROTECTION: Prevent self-deletion
        if user.username == request.user.username:
            messages.error(
                request, 
                '⚠️ You cannot delete your own account. This would permanently remove your access.'
            )
            return redirect('users:list')
        
        # Render delete confirmation template
        return render(request, 'users/users_delete.html', {'object': user})
    
    def post(self, request, pk):
        """Handle user deletion with protection."""
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # BACKEND PROTECTION: Prevent self-deletion
            if user.username == request.user.username:
                messages.error(
                    request, 
                    '⚠️ You cannot delete your own account. This would permanently remove your access.'
                )
                return redirect('users:list')
            
            user_name = user.get_display_name()
            user.delete()
            
            messages.success(
                request, 
                f'✅ User {user_name} has been deleted successfully!'
            )
            return redirect('users:list')
            
        except Exception as e:
            messages.error(request, f'❌ Error deleting user: {str(e)}')
            return redirect('users:list')


# ============================================================================
# User Role and Permission Management
# ============================================================================

class UserRoleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update user roles and permissions."""
    model = CustomUser
    form_class = UserRoleForm
    template_name = 'users/users_roles.html'
    permission_required = 'auth.change_user'
    
    def get_success_url(self):
        return reverse('users:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle successful role assignment."""
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Roles updated for {self.object.get_display_name()}!'
        )
        return response


class UserPermissionView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """View user permissions."""
    model = CustomUser
    template_name = 'users/users_permissions.html'
    permission_required = 'auth.view_user'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        """Add permission context."""
        context = super().get_context_data(**kwargs)
        user = self.object
        
        # Get all permissions (direct and through groups)
        all_permissions = user.get_all_permissions()
        group_permissions = user.get_group_permissions()
        direct_permissions = user.user_permissions.all()
        
        context['all_permissions'] = sorted(all_permissions)
        context['group_permissions'] = sorted(group_permissions)
        context['direct_permissions'] = direct_permissions
        
        return context


# ============================================================================
# User Profile Management
# ============================================================================

class UserProfileView(LoginRequiredMixin, DetailView):
    """Display current user's profile."""
    model = CustomUser
    template_name = 'users/users_profile.html'
    context_object_name = 'user_obj'
    
    def get_object(self):
        """Return current user."""
        return self.request.user


class UserProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit current user's profile."""
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'users/users_profile_edit.html'
    success_url = reverse_lazy('users:profile')
    
    def get_object(self):
        """Return current user."""
        return self.request.user
    
    def get_form(self, form_class=None):
        """Limit fields that user can edit."""
        form = super().get_form(form_class)
        # Remove sensitive fields from self-editing
        sensitive_fields = ['is_staff', 'is_superuser', 'is_active', 'is_active_employee']
        for field in sensitive_fields:
            if field in form.fields:
                del form.fields[field]
        return form


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Change user password."""
    template_name = 'users/users_password_change.html'
    success_url = reverse_lazy('users:profile')
    
    def form_valid(self, form):
        """Handle successful password change."""
        response = super().form_valid(form)
        messages.success(self.request, 'Password changed successfully!')
        return response


# ============================================================================
# Search and Lookup Views
# ============================================================================

class UserSearchView(LoginRequiredMixin, TemplateView):
    """Advanced user search page."""
    template_name = 'users/users_search.html'
    
    def get_context_data(self, **kwargs):
        """Add search form and results."""
        context = super().get_context_data(**kwargs)
        context['search_form'] = UserSearchForm()
        return context


@login_required
def user_lookup_by_employee_id(request, employee_id):
    """AJAX endpoint for employee ID lookup."""
    try:
        user = CustomUser.objects.get(employee_id=employee_id)
        return JsonResponse({
            'exists': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'name': user.get_full_name(),
                'email': user.email,
                'office': user.office,
                'designation': user.designation,
                'is_active': user.is_active and user.is_active_employee,
                'assigned_devices': user.get_assigned_devices_count()
            }
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'exists': False,
            'message': 'User with this employee ID does not exist.'
        })


# ============================================================================
# User Status Management
# ============================================================================

class UserActivateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Activate a user account with self-action protection.
    Location: Dhaka, Bangladesh - Parliament IT Management System
    """
    permission_required = 'auth.change_user'
    
    def post(self, request, pk):
        """Activate the specified user with protection."""
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # BACKEND PROTECTION: Prevent self-activation
            if user.username == request.user.username:
                messages.error(
                    request, 
                    '⚠️ You cannot activate your own account. Your account is already active.'
                )
                return redirect('users:list')
            
            # Check if user is already active
            if user.is_active:
                messages.info(
                    request, 
                    f'User {user.get_display_name()} is already active.'
                )
            else:
                # Activate user
                user.is_active = True
                if hasattr(user, 'is_active_employee'):
                    user.is_active_employee = True
                user.save()
                
                messages.success(
                    request, 
                    f'✅ User {user.get_display_name()} has been activated successfully! '
                    f'They can now access the system.'
                )
            
            # Redirect back to user list
            return redirect('users:list')
            
        except Exception as e:
            messages.error(request, f'❌ Error activating user: {str(e)}')
            return redirect('users:list')


class UserDeactivateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Deactivate a user account with self-action protection.
    Location: Dhaka, Bangladesh - Parliament IT Management System
    """
    permission_required = 'auth.change_user'
    
    def post(self, request, pk):
        """Deactivate the specified user with protection."""
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # BACKEND PROTECTION: Prevent self-deactivation
            if user.username == request.user.username:
                messages.error(
                    request, 
                    '⚠️ You cannot deactivate your own account. This would lock you out of the system.'
                )
                return redirect('users:list')
            
            # Check if user is already inactive
            if not user.is_active:
                messages.info(
                    request, 
                    f'User {user.get_display_name()} is already inactive.'
                )
            else:
                # Deactivate user
                user.is_active = False
                if hasattr(user, 'is_active_employee'):
                    user.is_active_employee = False
                user.save()
                
                messages.success(
                    request, 
                    f'✅ User {user.get_display_name()} has been deactivated successfully! '
                    f'They can no longer access the system.'
                )
            
            # Redirect back to user list
            return redirect('users:list')
            
        except Exception as e:
            messages.error(request, f'❌ Error deactivating user: {str(e)}')
            return redirect('users:list')
        

# ============================================================================
# AJAX Status Management (Optional - for dynamic updates)
# ============================================================================

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('auth.change_user', raise_exception=True)
def toggle_user_status_ajax(request, pk):
    """
    AJAX endpoint to toggle user active status with self-action protection.
    """
    if request.method == 'POST':
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            
            # BACKEND PROTECTION: Prevent self-toggle
            if user.username == request.user.username:
                return JsonResponse({
                    'success': False,
                    'message': '⚠️ You cannot change your own account status.'
                }, status=400)
            
            # Toggle status
            user.is_active = not user.is_active
            if hasattr(user, 'is_active_employee'):
                user.is_active_employee = user.is_active
            user.save()
            
            status_text = 'activated' if user.is_active else 'deactivated'
            
            return JsonResponse({
                'success': True,
                'is_active': user.is_active,
                'message': f'✅ User {user.get_display_name()} has been {status_text} successfully!',
                'username': user.username
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'❌ Error updating user status: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

# ============================================================================
# Utility Functions
# ============================================================================

def check_self_action(request_user, target_user):
    """
    Utility function to check if user is trying to perform action on themselves.
    Returns True if it's a self-action (should be prevented).
    """
    # Multiple checks for different scenarios
    if hasattr(target_user, 'username') and hasattr(request_user, 'username'):
        return target_user.username == request_user.username
    
    if hasattr(target_user, 'pk') and hasattr(request_user, 'pk'):
        return str(target_user.pk) == str(request_user.pk)
    
    if hasattr(target_user, 'id') and hasattr(request_user, 'id'):
        return target_user.id == request_user.id
    
    # Fallback: assume it's not a self-action if we can't determine
    return False
def get_user_display_name(user):
    """
    Get a user's display name safely.
    """
    if hasattr(user, 'get_display_name'):
        return user.get_display_name()
    elif hasattr(user, 'get_full_name') and user.get_full_name():
        return user.get_full_name()
    elif hasattr(user, 'username'):
        return user.username
    else:
        return str(user)


# ============================================================================
# Bulk Status Management (Optional)
# ============================================================================

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('auth.change_user', raise_exception=True), name='dispatch')
class BulkUserStatusView(View):
    """
    Handle bulk activation/deactivation of users.
    Location: Dhaka, Bangladesh - Parliament IT Management System
    """
    
    def post(self, request):
        """Handle bulk status changes."""
        try:
            action = request.POST.get('action')
            user_ids = request.POST.getlist('user_ids')
            
            if not action or not user_ids:
                messages.error(request, 'Invalid bulk action request.')
                return redirect('users:list')
            
            # Get users excluding current user
            users = CustomUser.objects.filter(
                id__in=user_ids
            ).exclude(id=request.user.id)
            
            if action == 'activate':
                # Bulk activate
                updated_count = users.update(
                    is_active=True,
                    is_active_employee=True
                )
                messages.success(
                    request, 
                    f'{updated_count} user(s) have been activated successfully!'
                )
                
            elif action == 'deactivate':
                # Bulk deactivate
                updated_count = users.update(
                    is_active=False,
                    is_active_employee=False
                )
                messages.success(
                    request, 
                    f'{updated_count} user(s) have been deactivated successfully!'
                )
            else:
                messages.error(request, 'Invalid action specified.')
            
            return redirect('users:list')
            
        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')
            return redirect('users:list')

# ============================================================================
# Status Checking Utilities
# ============================================================================

def get_user_status_summary():
    """
    Get summary of user statuses for dashboard/reports.
    Returns dictionary with counts.
    """
    try:
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        staff_users = CustomUser.objects.filter(is_staff=True, is_active=True).count()
        admin_users = CustomUser.objects.filter(is_superuser=True, is_active=True).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'staff_users': staff_users,
            'admin_users': admin_users,
            'activation_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0
        }
    except Exception:
        return {
            'total_users': 0,
            'active_users': 0,
            'inactive_users': 0,
            'staff_users': 0,
            'admin_users': 0,
            'activation_rate': 0
        }

# ============================================================================
# Reports and Export
# ============================================================================

class UserReportsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """User analytics and reports."""
    template_name = 'users/users_reports.html'
    permission_required = 'auth.view_user'
    
    def get_context_data(self, **kwargs):
        """Add report data to context."""
        context = super().get_context_data(**kwargs)
        
        # User statistics
        context['total_users'] = CustomUser.objects.count()
        context['active_users'] = CustomUser.get_active_employees().count()
        context['staff_users'] = CustomUser.objects.filter(is_staff=True).count()
        context['admin_users'] = CustomUser.objects.filter(is_superuser=True).count()
        
        # Users by office
        context['users_by_office'] = (
            CustomUser.objects.values('office')
            .annotate(count=Count('id'))
            .exclude(office='')
            .order_by('-count')[:10]
        )
        
        # Users by designation
        context['users_by_designation'] = (
            CustomUser.objects.values('designation')
            .annotate(count=Count('id'))
            .exclude(designation='')
            .order_by('-count')[:10]
        )
        
        # Users by groups
        context['users_by_group'] = (
            Group.objects.annotate(user_count=Count('user'))
            .order_by('-user_count')
        )
        
        return context


class UserExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Export user data."""
    permission_required = 'auth.view_user'
    
    def get(self, request):
        """Export users to CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Username', 'First Name', 'Last Name', 
            'Email', 'Office', 'Designation', 'Phone', 
            'Active', 'Staff', 'Groups', 'Created'
        ])
        
        users = CustomUser.objects.all().prefetch_related('groups')
        for user in users:
            groups = ', '.join([group.name for group in user.groups.all()])
            writer.writerow([
                user.employee_id,
                user.username,
                user.first_name,
                user.last_name,
                user.email,
                user.office,
                user.designation,
                user.phone_number,
                user.is_active and user.is_active_employee,
                user.is_staff,
                groups,
                user.created_at.strftime('%Y-%m-%d')
            ])
        
        return response