"""
Forms for Users app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines forms for user management, registration, and role assignment.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    """
    Form for creating new users with custom fields.
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
            'placeholder': 'Enter office name'
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+880XXXXXXXXX',
            'pattern': '^\+?1?\d{9,15}$',
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

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'employee_id', 'designation', 'office', 'phone_number',
            'profile_image', 'groups', 'password1', 'password2'
        )
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })

    def clean_employee_id(self):
        """Validate employee ID is unique and contains only numbers."""
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

    def save(self, commit=True):
        """Save user with additional fields."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.employee_id = self.cleaned_data['employee_id']
        user.designation = self.cleaned_data['designation']
        user.office = self.cleaned_data['office']
        user.phone_number = self.cleaned_data['phone_number']
        user.profile_image = self.cleaned_data['profile_image']
        
        if commit:
            user.save()
            # Add user to selected groups
            groups = self.cleaned_data['groups']
            for group in groups:
                user.groups.add(group)
            
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Form for editing existing users.
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

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'employee_id', 'designation', 'office', 'phone_number',
            'profile_image', 'is_active_employee', 'notes'
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password field from change form
        if 'password' in self.fields:
            del self.fields['password']

    def clean_employee_id(self):
        """Validate employee ID is unique (excluding current user)."""
        employee_id = self.cleaned_data['employee_id']
        
        # Check if employee_id already exists (excluding current user)
        existing_user = CustomUser.objects.filter(employee_id=employee_id).exclude(pk=self.instance.pk)
        if existing_user.exists():
            raise ValidationError('Employee ID already exists.')
        
        # Check if it contains only numbers
        if not employee_id.isdigit():
            raise ValidationError('Employee ID must contain only numbers.')
        
        return employee_id

    def clean_email(self):
        """Validate email is unique (excluding current user)."""
        email = self.cleaned_data['email']
        existing_user = CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk)
        if existing_user.exists():
            raise ValidationError('Email already exists.')
        return email


class UserRoleForm(forms.ModelForm):
    """
    Form for managing user roles and permissions.
    """
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select roles for this user'
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
        help_text='Grant all permissions'
    )

    class Meta:
        model = CustomUser
        fields = ('groups', 'user_permissions', 'is_staff', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Organize permissions by content type for better display
        self.fields['user_permissions'].queryset = Permission.objects.select_related('content_type').order_by('content_type__model', 'codename')


class UserSearchForm(forms.Form):
    """
    Form for searching and filtering users.
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
            'placeholder': 'Filter by office...'
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


class UserLoginForm(forms.Form):
    """
    Custom login form for PIMS.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Employee ID',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        """Authenticate user."""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate with username first
            user = authenticate(username=username, password=password)
            
            # If that fails, try to find user by employee_id
            if not user:
                try:
                    user_obj = CustomUser.objects.get(employee_id=username)
                    user = authenticate(username=user_obj.username, password=password)
                except CustomUser.DoesNotExist:
                    pass
            
            if not user:
                raise ValidationError('Invalid username/employee ID or password.')
            
            if not user.is_active:
                raise ValidationError('This account is inactive.')
            
            if not user.is_active_employee:
                raise ValidationError('This employee account is deactivated.')
            
            cleaned_data['user'] = user
        
        return cleaned_data


class PasswordResetForm(forms.Form):
    """
    Form for password reset functionality.
    """
    username_or_employee_id = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username or employee ID'
        })
    )
    
    def clean_username_or_employee_id(self):
        """Validate user exists."""
        identifier = self.cleaned_data['username_or_employee_id']
        
        # Try to find user by username or employee_id
        user = None
        try:
            user = CustomUser.objects.get(username=identifier)
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser.objects.get(employee_id=identifier)
            except CustomUser.DoesNotExist:
                raise ValidationError('User with this username or employee ID does not exist.')
        
        if not user.is_active or not user.is_active_employee:
            raise ValidationError('This account is inactive.')
        
        return identifier