"""
Enhanced Django Forms for PIMS User Management with PRP Integration
=================================================================

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration for Real Employee Data Collection
Context: Remove mock data functionality, implement real PRP API integration

Business Rules:
- PRP fields are read-only in PIMS interface
- No user creation from PIMS for PRP-managed users
- One-way sync: PRP → PIMS (PRP is authoritative source)
- Admin-controlled sync operations only
- Default password "12345678" for PRP users
- Username format: prp_{userId} for PRP users

Template Design: Flat design with high contrast (teal, orange, red)
Timezone: Asia/Dhaka
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import logging
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate

from .models import CustomUser

logger = logging.getLogger(__name__)


class CustomUserCreationForm(UserCreationForm):
    """
    Enhanced user creation form with PRP integration support.
    
    Features:
    - PRP user detection and validation
    - Read-only field handling for PRP data
    - Default password setting for PRP users
    - Enhanced validation for employee ID and email uniqueness
    """
    
    # Core user fields
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        }),
        help_text='Email address for system notifications'
    )
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    employee_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Employee ID (numbers only)'
        }),
        help_text='Employee ID from Parliament records'
    )
    
    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Job designation'
        })
    )
    
    office = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Department/Office name'
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mobile number'
        })
    )
    
    profile_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text='Profile photo (optional)'
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text='User access permissions'
    )
    
    # PRP-specific fields
    is_prp_managed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'prp_managed_checkbox'
        }),
        help_text='Check if this user is managed by PRP system. '
                  'PRP-managed users have read-only data that syncs from PRP API.'
    )

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'employee_id', 'designation', 'office', 'phone_number',
            'profile_image', 'groups', 'is_prp_managed', 
            'password1', 'password2'
        )
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username (for PRP users: prp_{userId})'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Customize password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password (PRP users: use "12345678")'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
        
        # Add PRP-specific help text
        self.fields['username'].help_text = (
            'Username for login. For PRP users, use format: prp_{userId}'
        )
        self.fields['employee_id'].help_text = (
            'Employee ID (numbers only). For PRP users, this maps to PRP userId.'
        )

    def clean_employee_id(self):
        """Validate employee ID with PRP considerations."""
        employee_id = self.cleaned_data['employee_id']
        
        # Check if employee_id already exists
        if CustomUser.objects.filter(employee_id=employee_id).exists():
            raise ValidationError('Employee ID already exists.')
        
        # Check if it contains only numbers
        if not employee_id.isdigit():
            raise ValidationError('Employee ID must contain only numbers.')
        
        return employee_id

    def clean_email(self):
        """Validate email is unique."""
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('Email already exists.')
        return email
    
    def clean_username(self):
        """Validate username with PRP format considerations."""
        username = self.cleaned_data['username']
        is_prp_managed = self.cleaned_data.get('is_prp_managed', False)
        
        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError('Username already exists.')
        
        # Validate PRP username format if marked as PRP-managed
        if is_prp_managed and not username.startswith('prp_'):
            raise ValidationError(
                'PRP-managed users must have username in format: prp_{userId}'
            )
        
        return username

    def save(self, commit=True):
        """Save user with PRP integration considerations."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.employee_id = self.cleaned_data['employee_id']
        user.designation = self.cleaned_data['designation']
        user.office = self.cleaned_data['office']
        user.phone_number = self.cleaned_data['phone_number']
        user.profile_image = self.cleaned_data['profile_image']
        user.is_prp_managed = self.cleaned_data['is_prp_managed']
        
        # Set default password for PRP users
        if user.is_prp_managed:
            user.set_password('12345678')  # Default PRP password
        
        if commit:
            user.save()
            # Add user to selected groups
            groups = self.cleaned_data['groups']
            for group in groups:
                user.groups.add(group)
            
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Enhanced form for editing existing users with PRP integration.
    
    Business Rules:
    - PRP-managed users have read-only core fields
    - Only admin status and groups can be modified for PRP users
    - Local PIMS users can edit all fields
    - Clear visual indicators for read-only fields
    """
    
    # Core user fields (potentially read-only for PRP users)
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    employee_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    office = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    profile_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'employee_id', 'designation', 'office', 'phone_number',
            'profile_image', 'groups', 'is_active', 'is_staff'
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove password field from edit form
        if 'password' in self.fields:
            del self.fields['password']
            
        # Check if this is a PRP-managed user
        instance = kwargs.get('instance')
        if instance and hasattr(instance, 'is_prp_managed') and instance.is_prp_managed:
            # Make PRP fields read-only
            readonly_fields = [
                'username', 'email', 'first_name', 'last_name',
                'employee_id', 'designation', 'office', 'phone_number'
            ]
            
            prp_note = "(Read-only: Synced from PRP)"
            
            for field_name in readonly_fields:
                if field_name in self.fields:
                    field = self.fields[field_name]
                    # Add read-only attributes
                    field.widget.attrs.update({
                        'readonly': True,
                        'class': field.widget.attrs.get('class', '') + ' prp-readonly-field',
                        'title': 'This field is managed by PRP and cannot be edited'
                    })
                    # Update help text
                    if field.help_text:
                        field.help_text = f"{field.help_text} {prp_note}"
                    else:
                        field.help_text = prp_note

    def clean(self):
        """Enhanced validation for PRP users."""
        cleaned_data = super().clean()
        instance = getattr(self, 'instance', None)
        
        if instance and hasattr(instance, 'is_prp_managed') and instance.is_prp_managed:
            # For PRP users, check if read-only fields were modified
            readonly_fields = [
                'username', 'email', 'first_name', 'last_name',
                'employee_id', 'designation', 'office', 'phone_number'
            ]
            
            for field_name in readonly_fields:
                if field_name in cleaned_data:
                    original_value = getattr(instance, field_name, '')
                    new_value = cleaned_data[field_name]
                    
                    if original_value != new_value:
                        raise ValidationError(
                            f'Field "{field_name}" cannot be modified for PRP-managed users. '
                            f'Please use PRP sync to update this information.'
                        )
        
        return cleaned_data


class UserSearchForm(forms.Form):
    """
    Enhanced form for searching and filtering users with PRP support.
    
    Features:
    - PRP user filtering
    - Sync status filtering for PRP users
    - Enhanced search across all user fields
    """
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, username, employee ID, or email...'
        })
    )
    
    office = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by office/department...'
        })
    )
    
    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by designation...'
        })
    )
    
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        empty_label="All Roles",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'All Users'),
            ('true', 'Active Only'),
            ('false', 'Inactive Only')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_staff = forms.ChoiceField(
        choices=[
            ('', 'All Users'),
            ('true', 'Staff Only'),
            ('false', 'Non-Staff Only')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # PRP-specific filters
    user_source = forms.ChoiceField(
        choices=[
            ('', 'All Users'),
            ('prp', 'PRP Users Only'),
            ('local', 'Local Users Only')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'title': 'Filter by user source (PRP vs Local)'
        }),
        help_text='Filter by user management source'
    )
    
    sync_status = forms.ChoiceField(
        choices=[
            ('', 'All PRP Users'),
            ('never_synced', 'Never Synced'),
            ('recently_synced', 'Recently Synced (24h)'),
            ('needs_sync', 'Needs Sync (>7 days)')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'title': 'Filter PRP users by sync status'
        }),
        help_text='Filter PRP users by synchronization status'
    )


class UserLoginForm(forms.Form):
    """
    Enhanced custom login form for PIMS with PRP User ID support.
    
    Features:
    - Support for PRP User ID login (prp_{userId} format)
    - Regular username/email login for local users
    - Default password handling for PRP users
    """
    
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or PRP User ID',
            'id': 'id_username'
        }),
        help_text='Enter your username or PRP User ID (format: prp_12345)'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'id_password'
        }),
        help_text='Default password for PRP users: 12345678'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_remember_me'
        }),
        label='Remember me'
    )

    def clean_username(self):
        """Enhanced username validation for PRP format."""
        username = self.cleaned_data['username']
        
        # Check if it's a PRP User ID format
        if username.startswith('prp_'):
            # Extract the user ID part
            user_id_part = username[4:]  # Remove 'prp_' prefix
            if not user_id_part.isdigit():
                raise ValidationError(
                    'Invalid PRP User ID format. Should be: prp_{userId} (e.g., prp_12345)'
                )
        
        return username


class PRPSyncForm(forms.Form):
    """
    Form for PRP synchronization operations.
    
    Admin-only form for controlling PRP sync operations.
    """
    
    sync_type = forms.ChoiceField(
        choices=[
            ('all', 'Sync All Departments'),
            ('department', 'Sync Specific Department'),
            ('user', 'Sync Specific User')
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the type of synchronization to perform'
    )
    
    department_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter department ID'
        }),
        help_text='Required when syncing specific department'
    )
    
    employee_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter employee ID'
        }),
        help_text='Required when syncing specific user'
    )
    
    force_sync = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Force sync even if user was recently updated'
    )

    def clean(self):
        """Validate sync parameters."""
        cleaned_data = super().clean()
        sync_type = cleaned_data.get('sync_type')
        department_id = cleaned_data.get('department_id')
        employee_id = cleaned_data.get('employee_id')
        
        if sync_type == 'department' and not department_id:
            raise ValidationError('Department ID is required for department sync.')
        
        if sync_type == 'user' and not employee_id:
            raise ValidationError('Employee ID is required for user sync.')
        
        return cleaned_data


class PRPConnectionTestForm(forms.Form):
    """
    Form for testing PRP API connection.
    
    Admin utility for verifying PRP integration status.
    """
    
    test_type = forms.ChoiceField(
        choices=[
            ('connection', 'Test API Connection'),
            ('authentication', 'Test Authentication'),
            ('departments', 'Test Department Fetch'),
            ('user_lookup', 'Test User Lookup')
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the test to perform'
    )
    
    test_employee_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Employee ID for user lookup test'
        }),
        help_text='Required only for user lookup test'
    )

    def clean(self):
        """Validate test parameters."""
        cleaned_data = super().clean()
        test_type = cleaned_data.get('test_type')
        test_employee_id = cleaned_data.get('test_employee_id')
        
        if test_type == 'user_lookup' and not test_employee_id:
            raise ValidationError('Employee ID is required for user lookup test.')
        
        return cleaned_data
    
    # Alias for backwards compatibility
CustomUserUpdateForm = CustomUserChangeForm  # Use existing CustomUserChangeForm


class UserRoleForm(forms.Form):
    """
    Form for managing user roles and group assignments.
    
    Used for bulk role assignments and individual user role management
    in PIMS with PRP integration support.
    """
    
    users = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select users to assign roles'
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select roles to assign to users'
    )
    
    action = forms.ChoiceField(
        choices=[
            ('add', 'Add Roles'),
            ('remove', 'Remove Roles'),
            ('replace', 'Replace All Roles')
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Choose how to apply the selected roles'
    )

    def clean(self):
        """Validate role assignment for PRP users."""
        cleaned_data = super().clean()
        users = cleaned_data.get('users', [])
        
        # Check if any selected users are PRP-managed
        prp_users = [user for user in users if hasattr(user, 'is_prp_managed') and user.is_prp_managed]
        
        if prp_users and cleaned_data.get('action') == 'replace':
            prp_usernames = [user.username for user in prp_users]
            raise ValidationError(
                f'Cannot replace all roles for PRP-managed users: {", ".join(prp_usernames)}. '
                'Only add/remove individual roles is allowed for PRP users.'
            )
        
        return cleaned_data


class CustomLoginForm(AuthenticationForm):
    """
    Enhanced custom login form for PIMS with PRP User ID support.
    
    Features:
    - Support for PRP User ID login (prp_{userId} format)
    - Regular username/email login for local users
    - Default password handling for PRP users
    - Compatible with Django's LoginView (inherits from AuthenticationForm)
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize form with PRP-aware styling."""
        super().__init__(*args, **kwargs)
        
        # Customize field styling and placeholders
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username or PRP User ID',
            'id': 'id_username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'id_password'
        })
        
        # Update help text for PRP integration
        self.fields['username'].help_text = 'Enter your username or PRP User ID (format: prp_12345)'
        self.fields['password'].help_text = 'Default password for PRP users: 12345678'
        
        # Add remember me field
        from django import forms
        self.fields['remember_me'] = forms.BooleanField(
            required=False,
            widget=forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_remember_me'
            }),
            label='Remember me'
        )

    def clean_username(self):
        """Enhanced username validation for PRP format."""
        username = self.cleaned_data['username']
        
        # Check if it's a PRP User ID format
        if username.startswith('prp_'):
            # Extract the user ID part
            user_id_part = username[4:]  # Remove 'prp_' prefix
            if not user_id_part.isdigit():
                raise ValidationError(
                    'Invalid PRP User ID format. Should be: prp_{userId} (e.g., prp_12345)'
                )
        
        return username

    def clean(self):
        """Enhanced authentication with PRP user support."""
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            # Authenticate using Django's authenticate function
            self.user_cache = authenticate(
                self.request, 
                username=username, 
                password=password
            )
            
            if self.user_cache is None:
                # Check if this might be a PRP user that needs to be synced
                if self._is_potential_prp_user(username):
                    raise ValidationError(
                        'User not found in PIMS. Contact admin to sync your PRP account.',
                        code='prp_user_not_synced'
                    )
                else:
                    raise ValidationError(
                        'Please enter a correct username and password. Note that both fields may be case-sensitive.',
                        code='invalid_login'
                    )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
    
    def _is_potential_prp_user(self, username: str) -> bool:
        """Check if username pattern suggests a PRP user."""
        # PRP users might login with employee ID directly or prp_ format
        return (username.isdigit() and len(username) >= 4) or username.startswith('prp_')


class CustomPasswordResetForm(forms.Form):
    """
    Custom password reset form with PRP user awareness.
    
    Note: PRP users cannot reset passwords (they use default "12345678")
    """
    
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'id': 'id_email'
        }),
        help_text='Enter the email address associated with your account'
    )

    def clean_email(self):
        """Check if email belongs to PRP user."""
        email = self.cleaned_data['email']
        
        try:
            user = CustomUser.objects.get(email=email)
            if hasattr(user, 'is_prp_managed') and user.is_prp_managed:
                raise ValidationError(
                    'PRP-managed users cannot reset passwords. '
                    'Please use your default PRP password (12345678) or contact admin.'
                )
        except CustomUser.DoesNotExist:
            # User doesn't exist - let Django handle this in the view
            pass
        
        return email