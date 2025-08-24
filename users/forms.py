"""
Forms for Users app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat, Dhaka

Enhanced forms with PRP (Parliament Resource Portal) Integration
This module defines forms for user management with conditional read-only behavior
for PRP-managed users, maintaining backwards compatibility.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Handle PRP user forms with read-only PRP-sourced fields
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    """
    Enhanced form for creating new users with PRP integration support.
    
    Key Features:
    - PRP user detection and field locking
    - Conditional validation based on user source
    - Visual indicators for PRP vs local users
    - Maintains existing functionality for local users
    """
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    
    employee_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter employee ID (numbers only)',
            'pattern': '[0-9]+',
            'title': 'Employee ID must contain only numbers'
        })
    )
    
    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter job designation'
        })
    )
    
    office = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter office/department name'
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+880XXXXXXXXX',
            'pattern': r'^\+?1?\d{9,15}$', 
            'title': 'Phone number format: +880XXXXXXXXX'
        })
    )
    
    profile_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text='Select user roles/groups'
    )
    
    # PRP Integration Fields
    is_prp_managed = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'onchange': 'togglePRPFieldsReadonly(this.checked)'
        }),
        help_text='Check if this user is managed by Parliament Resource Portal (PRP). '
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
    
    Key Features:
    - Conditional read-only fields for PRP users
    - Visual indicators for PRP-sourced data
    - Preserves admin override capabilities
    - Maintains validation rules for local users
    """
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    employee_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'pattern': '[0-9]+',
            'title': 'Employee ID must contain only numbers'
        })
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
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    is_active_employee = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Administrative notes...'
        })
    )
    
    # PRP Integration Fields (read-only display)
    is_prp_managed = forms.BooleanField(
        required=False,
        disabled=True,  # Cannot be changed after creation
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'disabled': 'disabled'
        }),
        help_text='Indicates if this user is managed by PRP. This cannot be changed after user creation.'
    )
    
    prp_last_sync = forms.DateTimeField(
        required=False,
        disabled=True,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        help_text='Last synchronization timestamp from Parliament Resource Portal.'
    )

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'employee_id', 'designation', 'office', 'phone_number',
            'profile_image', 'is_active_employee', 'notes',
            'is_prp_managed', 'prp_last_sync'
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove password field from change form
        if 'password' in self.fields:
            del self.fields['password']
        
        # Apply PRP read-only logic if editing existing user
        if self.instance and self.instance.pk and self.instance.is_prp_managed:
            self._apply_prp_readonly_styling()
    
    def _apply_prp_readonly_styling(self):
        """Apply read-only styling and behavior to PRP-sourced fields."""
        prp_readonly_fields = self.instance.get_prp_readonly_fields()
        
        for field_name in prp_readonly_fields:
            if field_name in self.fields:
                field = self.fields[field_name]
                
                # Make field read-only
                field.disabled = True
                field.widget.attrs.update({
                    'readonly': 'readonly',
                    'style': 'background-color: #f8f9fa; border-color: #dee2e6; color: #6c757d;',
                    'title': 'This field is managed by Parliament Resource Portal (PRP) and cannot be edited.'
                })
                
                # Update help text with PRP indicator
                prp_help = "🏛️ This field is managed by Parliament Resource Portal (PRP) and cannot be edited."
                if field.help_text:
                    field.help_text = f"{field.help_text} {prp_help}"
                else:
                    field.help_text = prp_help
        
        # Add visual indicator to form
        if hasattr(self, 'helper'):
            self.helper.form_tag = False
    
    def _get_prp_field_widget(self, field_name, widget_class=forms.TextInput):
        """Get styled read-only widget for PRP fields."""
        return widget_class(attrs={
            'class': 'form-control prp-readonly',
            'readonly': 'readonly',
            'style': (
                'background-color: #f8f9fa; '
                'border-color: #28a745; '
                'color: #495057; '
                'position: relative;'
            ),
            'title': 'This field is managed by Parliament Resource Portal (PRP)',
            'data-prp-field': 'true'
        })

    def clean_employee_id(self):
        """Validate employee ID with PRP considerations."""
        employee_id = self.cleaned_data['employee_id']
        
        # Skip validation for PRP users (their data comes from PRP)
        if self.instance and self.instance.is_prp_managed:
            return employee_id
        
        # Check if employee_id already exists (excluding current user)
        existing_user = CustomUser.objects.filter(employee_id=employee_id).exclude(pk=self.instance.pk)
        if existing_user.exists():
            raise ValidationError('Employee ID already exists.')
        
        # Check if it contains only numbers
        if not employee_id.isdigit():
            raise ValidationError('Employee ID must contain only numbers.')
        
        return employee_id

    def clean_email(self):
        """Validate email with PRP considerations."""
        email = self.cleaned_data['email']
        
        # Skip validation for PRP users (their data comes from PRP)
        if self.instance and self.instance.is_prp_managed:
            return email
        
        # Check if email already exists (excluding current user)
        existing_user = CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk)
        if existing_user.exists():
            raise ValidationError('Email already exists.')
        
        return email
    
    def clean(self):
        """Overall form validation with PRP business rules."""
        cleaned_data = super().clean()
        
        # PRP users cannot be created through PIMS interface
        is_prp_managed = cleaned_data.get('is_prp_managed', False)
        if is_prp_managed and not self.instance.pk:
            raise ValidationError(
                'PRP-managed users cannot be created manually. '
                'They are automatically created during PRP synchronization.'
            )
        
        # Prevent changing PRP management flag after creation
        if self.instance.pk and self.instance.is_prp_managed != is_prp_managed:
            raise ValidationError(
                'PRP management status cannot be changed after user creation.'
            )
        
        return cleaned_data


class CustomUserChangeForm(UserChangeForm):
    """
    Enhanced form for editing existing users with comprehensive PRP support.
    
    Features:
    - Intelligent field locking for PRP users
    - Visual PRP indicators and styling
    - Preserved admin override for specific fields
    - Enhanced validation and error messaging
    """
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    employee_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'pattern': '[0-9]+',
            'title': 'Employee ID must contain only numbers'
        })
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
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    is_active_employee = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Employee active status. Can be overridden by PIMS admin even for PRP users.'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Administrative notes...'
        })
    )
    
    # PRP Integration Display Fields
    is_prp_managed = forms.BooleanField(
        required=False,
        disabled=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'disabled': 'disabled'
        }),
        help_text='Indicates if this user is managed by Parliament Resource Portal (PRP). Cannot be changed after creation.'
    )
    
    prp_last_sync = forms.DateTimeField(
        required=False,
        disabled=True,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #e9ecef;'
        }),
        help_text='Last synchronization from Parliament Resource Portal (Asia/Dhaka timezone).'
    )

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'employee_id', 'designation', 'office', 'phone_number',
            'profile_image', 'is_active_employee', 'notes',
            'is_prp_managed', 'prp_last_sync'
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove password field from change form
        if 'password' in self.fields:
            del self.fields['password']
        
        # Apply PRP-specific form modifications
        if self.instance and self.instance.pk:
            if self.instance.is_prp_managed:
                self._apply_prp_readonly_behavior()
            self._add_prp_status_indicators()
    
    def _apply_prp_readonly_behavior(self):
        """Apply comprehensive read-only behavior for PRP users."""
        # Get PRP read-only fields from model
        prp_readonly_fields = self.instance.get_prp_readonly_fields()
        
        for field_name in prp_readonly_fields:
            if field_name in self.fields:
                field = self.fields[field_name]
                
                # Make field read-only
                field.disabled = True
                
                # Apply PRP-specific styling
                current_attrs = field.widget.attrs
                prp_styling = {
                    'readonly': 'readonly',
                    'style': (
                        'background-color: #f8f9fa; '
                        'border-left: 4px solid #28a745; '
                        'color: #495057; '
                        'position: relative;'
                    ),
                    'title': 'This field is managed by Parliament Resource Portal (PRP) and cannot be edited.',
                    'data-prp-field': 'true'
                }
                current_attrs.update(prp_styling)
                
                # Add PRP indicator to help text
                prp_indicator = "🏛️ Managed by Parliament Resource Portal (PRP) - Read Only"
                if field.help_text:
                    field.help_text = f"{prp_indicator}. {field.help_text}"
                else:
                    field.help_text = prp_indicator
    
    def _add_prp_status_indicators(self):
        """Add visual status indicators for PRP vs local users."""
        if self.instance.is_prp_managed:
            # Add PRP status indicator to username field
            username_field = self.fields.get('username')
            if username_field:
                username_field.help_text = (
                    '🏛️ <strong style="color: #28a745;">PRP User</strong> - '
                    'This user is managed by Parliament Resource Portal. '
                    'Username cannot be changed.'
                )
                username_field.disabled = True
        else:
            # Add local user indicator
            username_field = self.fields.get('username')
            if username_field:
                username_field.help_text = (
                    '🏢 <strong style="color: #6c757d;">Local User</strong> - '
                    'This user is managed locally in PIMS.'
                )

    def clean_employee_id(self):
        """Validate employee ID with PRP considerations."""
        employee_id = self.cleaned_data['employee_id']
        
        # Skip validation for PRP users (field is read-only anyway)
        if self.instance and self.instance.is_prp_managed:
            return employee_id
        
        # Check if employee_id already exists (excluding current user)
        existing_user = CustomUser.objects.filter(employee_id=employee_id).exclude(pk=self.instance.pk)
        if existing_user.exists():
            raise ValidationError('Employee ID already exists.')
        
        # Check if it contains only numbers
        if not employee_id.isdigit():
            raise ValidationError('Employee ID must contain only numbers.')
        
        return employee_id

    def clean_email(self):
        """Validate email with PRP considerations."""
        email = self.cleaned_data['email']
        
        # Skip validation for PRP users (field is read-only anyway)
        if self.instance and self.instance.is_prp_managed:
            return email
        
        # Check if email already exists (excluding current user)
        existing_user = CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk)
        if existing_user.exists():
            raise ValidationError('Email already exists.')
        
        return email
    
    def clean(self):
        """Enhanced form validation with PRP business rules."""
        cleaned_data = super().clean()
        
        # Prevent editing PRP-sourced fields (additional protection)
        if self.instance and self.instance.is_prp_managed:
            prp_readonly_fields = self.instance.get_prp_readonly_fields()
            
            for field_name in prp_readonly_fields:
                if field_name in self.changed_data:
                    raise ValidationError(
                        f'Field "{field_name}" cannot be modified for PRP-managed users. '
                        'This data is managed by Parliament Resource Portal.'
                    )
        
        return cleaned_data


class PRPUserLoginForm(forms.Form):
    """
    Enhanced login form supporting both PRP User ID and regular username.
    
    Features:
    - Accepts PRP User ID or regular username
    - Automatic PRP user detection
    - Support for default PRP password (12345678)
    - Enhanced error messages for PRP users
    """
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username, Employee ID, or PRP User ID',
            'autofocus': True,
            'title': 'Enter your username, employee ID, or PRP User ID'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password (PRP users: 12345678)'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Keep me logged in on this device'
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        """Enhanced authentication supporting PRP User ID login."""
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            # Try multiple authentication methods
            user = self._authenticate_user(username, password)
            
            if user is None:
                raise ValidationError(
                    'Invalid login credentials. Please check your username/employee ID and password.',
                    code='invalid_login'
                )
            
            if not user.is_active:
                raise ValidationError(
                    'This account is inactive. Please contact the administrator.',
                    code='inactive_account'
                )
            
            if user.is_prp_managed and not user.is_active_employee:
                raise ValidationError(
                    'Your account is currently inactive in the Parliament system. '
                    'Please contact the administrator for assistance.',
                    code='inactive_employee'
                )
            
            self.user_cache = user

        return self.cleaned_data
    
    def _authenticate_user(self, username, password):
        """
        Try multiple authentication methods for PRP and local users.
        
        Authentication priority:
        1. Direct username authentication
        2. Employee ID authentication
        3. PRP username format (prp_{userId})
        """
        # Method 1: Direct username authentication
        user = authenticate(
            self.request,
            username=username,
            password=password
        )
        if user:
            return user
        
        # Method 2: Try to find user by employee ID
        try:
            user_by_employee_id = CustomUser.objects.get(employee_id=username)
            user = authenticate(
                self.request,
                username=user_by_employee_id.username,
                password=password
            )
            if user:
                return user
        except CustomUser.DoesNotExist:
            pass
        
        # Method 3: Try PRP username format (prp_{userId})
        if not username.startswith('prp_'):
            prp_username = f"prp_{username}"
            user = authenticate(
                self.request,
                username=prp_username,
                password=password
            )
            if user:
                return user
        
        return None

    def get_user(self):
        """Return the authenticated user."""
        return self.user_cache


class UserRoleForm(forms.ModelForm):
    """
    Enhanced form for managing user roles and permissions with PRP awareness.
    
    Features:
    - PRP user role restrictions
    - Visual indicators for PRP vs local users
    - Enhanced permission management
    """
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select roles for this user. PRP users can have additional PIMS roles.'
    )
    
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select specific permissions for this user'
    )
    
    is_staff = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Allow access to admin site'
    )
    
    is_superuser = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Grant all permissions (use with caution)'
    )

    class Meta:
        model = CustomUser
        fields = ('groups', 'user_permissions', 'is_staff', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Organize permissions by content type for better display
        self.fields['user_permissions'].queryset = Permission.objects.select_related(
            'content_type'
        ).order_by('content_type__model', 'codename')
        
        # Add PRP user indicator if applicable
        if self.instance and self.instance.is_prp_managed:
            for field_name in ['groups', 'user_permissions', 'is_staff', 'is_superuser']:
                if field_name in self.fields:
                    field = self.fields[field_name]
                    prp_note = "Note: This is a PRP-managed user from Parliament Resource Portal."
                    if field.help_text:
                        field.help_text = f"{field.help_text} {prp_note}"
                    else:
                        field.help_text = prp_note


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
    - Multi-format username support (username, employee ID, PRP User ID)
    - PRP user detection and enhanced messaging
    - Session management options
    - Bangladesh context-aware help text
    """
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username, Employee ID, or PRP User ID',
            'autofocus': True,
            'title': 'Enter your username, employee ID, or PRP User ID'
        }),
        help_text='Use your Employee ID, PRP User ID, or assigned username'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password (PRP users: 12345678)'
        }),
        help_text='Default password for PRP users is: 12345678'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Keep me logged in on this device'
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        """Enhanced authentication with comprehensive PRP User ID support."""
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            # Try multiple authentication methods for PRP and local users
            user = self._authenticate_with_multiple_methods(username, password)
            
            if user is None:
                raise ValidationError(
                    'Invalid login credentials. For PRP users, use your PRP User ID and password "12345678".',
                    code='invalid_login'
                )
            
            # Check account status
            if not user.is_active:
                raise ValidationError(
                    'This account is inactive. Please contact the Parliament IT administrator.',
                    code='inactive_account'
                )
            
            # Special handling for PRP users
            if user.is_prp_managed and not user.is_active_employee:
                raise ValidationError(
                    'Your Parliament account is currently inactive. Please contact the Parliament HR department.',
                    code='inactive_prp_employee'
                )
            
            self.user_cache = user

        return self.cleaned_data
    
    def _authenticate_with_multiple_methods(self, input_username, password):
        """
        Comprehensive authentication supporting multiple username formats.
        
        Authentication Methods (in priority order):
        1. Direct username authentication
        2. Employee ID to username lookup
        3. PRP User ID with prp_ prefix
        4. Raw PRP User ID authentication
        
        Args:
            input_username: User input (can be username, employee ID, or PRP User ID)
            password: User password
            
        Returns:
            CustomUser instance if authenticated, None otherwise
        """
        
        # Method 1: Direct username authentication
        user = authenticate(
            self.request,
            username=input_username,
            password=password
        )
        if user:
            return user
        
        # Method 2: Try to find user by employee ID and authenticate with their username
        try:
            user_by_employee_id = CustomUser.objects.get(employee_id=input_username)
            user = authenticate(
                self.request,
                username=user_by_employee_id.username,
                password=password
            )
            if user:
                return user
        except CustomUser.DoesNotExist:
            pass
        
        # Method 3: Try PRP username format (prp_{userId}) if not already in that format
        if not input_username.startswith('prp_'):
            prp_username = f"prp_{input_username}"
            user = authenticate(
                self.request,
                username=prp_username,
                password=password
            )
            if user:
                return user
        
        # Method 4: For PRP users, try finding by employee_id matching the number part
        if input_username.startswith('prp_'):
            prp_user_id = input_username[4:]  # Remove 'prp_' prefix
            try:
                prp_user = CustomUser.objects.get(
                    employee_id=prp_user_id,
                    is_prp_managed=True
                )
                user = authenticate(
                    self.request,
                    username=prp_user.username,
                    password=password
                )
                if user:
                    return user
            except CustomUser.DoesNotExist:
                pass
        
        return None

    def get_user(self):
        """Return the authenticated user."""
        return self.user_cache


class PasswordResetForm(forms.Form):
    """
    Enhanced password reset form with PRP user considerations.
    
    Features:
    - PRP user detection and messaging
    - Employee ID-based email lookup
    - Enhanced error messaging for Bangladesh Parliament context
    """
    
    email_or_employee_id = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address or employee ID',
            'title': 'Enter your email address or employee ID for password reset'
        }),
        help_text='Enter your email address or employee ID to reset your password'
    )

    def clean_email_or_employee_id(self):
        """Find user by email or employee ID."""
        input_value = self.cleaned_data['email_or_employee_id']
        
        # Try to find user by email first
        try:
            user = CustomUser.objects.get(email=input_value, is_active=True)
            return user.email
        except CustomUser.DoesNotExist:
            pass
        
        # Try to find user by employee ID
        try:
            user = CustomUser.objects.get(employee_id=input_value, is_active=True)
            if not user.email:
                raise ValidationError(
                    'No email address associated with this employee ID. '
                    'Please contact the Parliament IT administrator.'
                )
            return user.email
        except CustomUser.DoesNotExist:
            pass
        
        # Check if it's a PRP user and provide helpful message
        try:
            if input_value.isdigit():
                prp_user = CustomUser.objects.get(
                    employee_id=input_value, 
                    is_prp_managed=True
                )
                raise ValidationError(
                    'This is a PRP-managed account. PRP users use the default password "12345678". '
                    'If you need to change your password, please contact the Parliament IT administrator.'
                )
        except CustomUser.DoesNotExist:
            pass
        
        raise ValidationError(
            'No active user found with this email address or employee ID. '
            'Please verify your information or contact the Parliament IT administrator.'
        )


class PRPSyncForm(forms.Form):
    """
    Form for manual PRP synchronization operations.
    
    Features:
    - Department selection for targeted sync
    - Sync options and preferences
    - Admin-only operations with confirmations
    """
    
    SYNC_TYPE_CHOICES = [
        ('all', 'Sync All Departments'),
        ('department', 'Sync Specific Department'),
        ('user', 'Sync Specific User'),
        ('status_only', 'Update Status Only')
    ]
    
    sync_type = forms.ChoiceField(
        choices=SYNC_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text='Select the type of synchronization to perform'
    )
    
    department_id = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter department ID',
            'min': '1'
        }),
        help_text='Required for department-specific sync. Get ID from PRP departments list.'
    )
    
    employee_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter employee ID',
            'pattern': '[0-9]+',
            'title': 'Employee ID must contain only numbers'
        }),
        help_text='Required for user-specific sync. Use PRP userId.'
    )
    
    force_sync = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Force sync even if recently synced (ignore timestamp checks)'
    )
    
    dry_run = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Preview changes without applying them (for testing purposes)'
    )

    def clean(self):
        """Validate sync form based on selected sync type."""
        cleaned_data = super().clean()
        sync_type = cleaned_data.get('sync_type')
        department_id = cleaned_data.get('department_id')
        employee_id = cleaned_data.get('employee_id')
        
        # Validate required fields based on sync type
        if sync_type == 'department' and not department_id:
            raise ValidationError('Department ID is required for department-specific sync.')
        
        if sync_type == 'user' and not employee_id:
            raise ValidationError('Employee ID is required for user-specific sync.')
        
        # Validate employee ID format if provided
        if employee_id and not employee_id.isdigit():
            raise ValidationError('Employee ID must contain only numbers.')
        
        return cleaned_data


class BulkUserOperationForm(forms.Form):
    """
    Form for bulk operations on users with PRP awareness.
    
    Features:
    - Bulk status updates with PRP considerations
    - Role assignment for multiple users
    - PRP sync operations for selected users
    """
    
    BULK_OPERATION_CHOICES = [
        ('activate', 'Activate Users'),
        ('deactivate', 'Deactivate Users'),
        ('add_to_group', 'Add to Group'),
        ('remove_from_group', 'Remove from Group'),
        ('sync_prp', 'Sync PRP Users'),
        ('export', 'Export User Data')
    ]
    
    operation = forms.ChoiceField(
        choices=BULK_OPERATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the operation to perform on selected users'
    )
    
    target_group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select group for add/remove operations'
    )
    
    confirm_operation = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='I confirm that I want to perform this bulk operation'
    )
    
    selected_users = forms.CharField(
        widget=forms.HiddenInput(),
        help_text='Comma-separated list of user IDs'
    )

    def clean(self):
        """Validate bulk operation form."""
        cleaned_data = super().clean()
        operation = cleaned_data.get('operation')
        target_group = cleaned_data.get('target_group')
        
        # Validate group selection for group operations
        if operation in ['add_to_group', 'remove_from_group'] and not target_group:
            raise ValidationError('Please select a target group for this operation.')
        
        return cleaned_data


class PRPUserFilterForm(forms.Form):
    """
    Specialized form for filtering and managing PRP users.
    
    Features:
    - PRP-specific filtering options
    - Sync status management
    - Department-based filtering
    """
    
    SYNC_STATUS_CHOICES = [
        ('', 'All PRP Users'),
        ('never_synced', 'Never Synced'),
        ('recently_synced', 'Recently Synced (24h)'),
        ('needs_sync', 'Needs Sync (>7 days)'),
        ('sync_errors', 'Sync Errors')
    ]
    
    sync_status = forms.ChoiceField(
        choices=SYNC_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Filter PRP users by synchronization status'
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by Parliament department...'
        }),
        help_text='Filter by department/office from Parliament Resource Portal'
    )
    
    active_status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('active', 'Active Employees'),
            ('inactive', 'Inactive Employees'),
            ('admin_override', 'Admin Override (Inactive in PIMS, Active in PRP)')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Filter by employee active status'
    )


class UserPermissionForm(forms.ModelForm):
    """
    Enhanced form for detailed user permission management.
    
    Features:
    - Grouped permission display
    - PRP user permission warnings
    - Visual permission hierarchy
    """
    
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        help_text='Select specific permissions for this user'
    )

    class Meta:
        model = CustomUser
        fields = ['user_permissions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Group permissions by content type for better organization
        permissions_by_app = {}
        for permission in Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'content_type__model', 'codename'
        ):
            app_label = permission.content_type.app_label
            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = []
            permissions_by_app[app_label].append(permission)
        
        # Store grouped permissions for template use
        self.permissions_by_app = permissions_by_app
        
        # Add PRP warning if applicable
        if self.instance and self.instance.is_prp_managed:
            self.fields['user_permissions'].help_text = (
                '🏛️ <strong>PRP User</strong>: This user is managed by Parliament Resource Portal. '
                'Permissions can be assigned normally, but user data is read-only. '
                'Select specific permissions for this user.'
            )


class QuickUserCreateForm(forms.ModelForm):
    """
    Simplified form for quick user creation (admin use).
    
    Features:
    - Minimal required fields
    - Auto-generated username option
    - PRP user creation prevention
    """
    
    class Meta:
        model = CustomUser
        fields = [
            'employee_id', 'first_name', 'last_name', 
            'email', 'designation', 'office'
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Employee ID (numbers only)',
                'pattern': '[0-9]+',
                'title': 'Employee ID must contain only numbers'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'designation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Job designation'
            }),
            'office': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Office/Department'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['employee_id'].help_text = (
            'Unique employee identifier (numbers only). '
            'Note: PRP users are created automatically during sync.'
        )

    def clean_employee_id(self):
        """Validate employee ID for quick creation."""
        employee_id = self.cleaned_data['employee_id']
        
        # Check if employee_id already exists
        if CustomUser.objects.filter(employee_id=employee_id).exists():
            existing_user = CustomUser.objects.get(employee_id=employee_id)
            if existing_user.is_prp_managed:
                raise ValidationError(
                    f'Employee ID {employee_id} belongs to a PRP user. '
                    'PRP users are managed automatically through synchronization.'
                )
            else:
                raise ValidationError('Employee ID already exists.')
        
        # Check if it contains only numbers
        if not employee_id.isdigit():
            raise ValidationError('Employee ID must contain only numbers.')
        
        return employee_id

    def save(self, commit=True):
        """Save with auto-generated username and default settings."""
        user = super().save(commit=False)
        
        # Auto-generate username based on employee ID
        user.username = f"user_{user.employee_id}"
        
        # Set default password
        user.set_password('pims2025')  # Default password for local users
        
        # Mark as local user (not PRP-managed)
        user.is_prp_managed = False
        
        if commit:
            user.save()
        
        return user


# ============================================================================
# UTILITY FUNCTIONS FOR FORMS
# ============================================================================

def get_prp_readonly_widget_attrs():
    """
    Get standardized widget attributes for PRP read-only fields.
    
    Returns consistent styling across all PRP read-only fields following
    the template design pattern rules.
    """
    return {
        'readonly': 'readonly',
        'style': (
            'background-color: #f8f9fa; '
            'border-left: 4px solid #28a745; '
            'color: #495057; '
            'cursor: not-allowed;'
        ),
        'title': 'This field is managed by Parliament Resource Portal (PRP)',
        'data-prp-field': 'true',
        'tabindex': '-1'  # Skip in tab navigation
    }


def apply_prp_styling_to_field(field, field_name):
    """
    Apply consistent PRP styling to a form field.
    
    Args:
        field: Django form field
        field_name: Name of the field
        
    Updates field widget attributes and help text with PRP indicators.
    """
    # Apply PRP read-only styling
    prp_attrs = get_prp_readonly_widget_attrs()
    field.widget.attrs.update(prp_attrs)
    
    # Add PRP indicator to help text
    prp_indicator = "🏛️ Managed by Parliament Resource Portal (PRP)"
    if field.help_text:
        field.help_text = f"{prp_indicator}. {field.help_text}"
    else:
        field.help_text = prp_indicator
    
    # Mark as disabled for form processing
    field.disabled = True


def validate_prp_username_format(username, is_prp_managed=False):
    """
    Validate username format for PRP users.
    
    Args:
        username: Username to validate
        is_prp_managed: Whether user is PRP-managed
        
    Returns:
        bool: True if valid
        
    Raises:
        ValidationError: If format is invalid
    """
    if is_prp_managed:
        if not username.startswith('prp_'):
            raise ValidationError(
                'PRP-managed users must have username in format: prp_{userId}'
            )
        
        # Extract and validate user ID part
        user_id_part = username[4:]  # Remove 'prp_' prefix
        if not user_id_part.isdigit():
            raise ValidationError(
                'PRP username format must be: prp_{numeric_userId}'
            )
    
    return True


# ============================================================================
# CUSTOM WIDGETS FOR PRP INTEGRATION
# ============================================================================

class PRPReadOnlyWidget(forms.TextInput):
    """
    Custom widget for PRP read-only fields with enhanced styling.
    
    Features:
    - Visual PRP indicators
    - Consistent styling across all PRP fields
    - Accessibility support
    """
    
    def __init__(self, attrs=None):
        default_attrs = get_prp_readonly_widget_attrs()
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render widget with PRP indicator."""
        html = super().render(name, value, attrs, renderer)
        
        # Add PRP indicator icon
        prp_indicator = (
            '<span class="prp-field-indicator" '
            'style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); '
            'color: #28a745; font-size: 14px;" '
            'title="Parliament Resource Portal (PRP) Field">🏛️</span>'
        )
        
        # Wrap in relative container for indicator positioning
        return mark_safe(
            f'<div style="position: relative; display: inline-block; width: 100%;">'
            f'{html}{prp_indicator}</div>'
        )


class PRPImageWidget(forms.ClearableFileInput):
    """
    Custom widget for PRP profile images with read-only styling.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control',
            'disabled': 'disabled',
            'style': 'background-color: #f8f9fa; border-color: #28a745;',
            'title': 'Profile image is managed by Parliament Resource Portal (PRP)'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


# ============================================================================
# BACKWARDS COMPATIBILITY ALIASES
# ============================================================================

# Maintain backwards compatibility with existing code
UserLoginForm = PRPUserLoginForm  # Use enhanced login form as default