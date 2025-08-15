"""
Forms for Assignments app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines forms for assignment management including:
- AssignmentForm: Create and edit device assignments
- AssignmentFilterForm: Filter assignments with advanced search
- QuickAssignmentForm: Simplified form for quick assignments
- AssignmentReturnForm: Handle device returns
- AssignmentTransferForm: Transfer assignments between users/locations

Features:
- Smart device filtering (only available devices)
- User-friendly widgets with Bootstrap 5.3 styling
- Real-time validation and error handling
- Consistent design following PIMS template patterns
- Integration with devices, users, and locations apps
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

from .models import Assignment, AssignmentQRCode
from devices.models import Device
from locations.models import Location

User = get_user_model()


class AssignmentForm(forms.ModelForm):
    """
    Main form for creating and editing assignments.
    Includes all assignment fields with proper validation and styling.
    """
    
    class Meta:
        model = Assignment
        fields = [
            'device', 'assigned_to', 'assigned_location',
            'assignment_type', 'assigned_date', 'expected_return_date',
            'purpose', 'assignment_notes',
            'condition_at_assignment',
            'emergency_contact', 'emergency_phone',
        ]
        
        widgets = {
            'device': forms.Select(attrs={
                'class': 'form-select device-selector',
                'data-placeholder': 'Select an available device...'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select employee-selector',
                'data-placeholder': 'Select employee...'
            }),
            'assigned_location': forms.Select(attrs={
                'class': 'form-select location-selector',
                'data-placeholder': 'Select location (optional)...'
            }),
            'assignment_type': forms.Select(attrs={
                'class': 'form-select assignment-type-selector'
            }),
            'assigned_date': forms.DateInput(attrs={
                'class': 'form-control date-picker',
                'type': 'date'
            }),
            'expected_return_date': forms.DateInput(attrs={
                'class': 'form-control date-picker return-date',
                'type': 'date'
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter assignment purpose or reason...',
                'maxlength': 200
            }),
            'assignment_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes about this assignment...'
            }),
            'condition_at_assignment': forms.Select(attrs={
                'class': 'form-select condition-selector'
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency contact person name...'
            }),
            'emergency_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '01712345678',
                'pattern': '[0-9+\-\s]+'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with filtered querysets and defaults."""
        self.user = kwargs.pop('user', None)
        self.editing = kwargs.get('instance') is not None
        super().__init__(*args, **kwargs)
        
        # Filter devices - only show available devices or current device (for editing)
        if self.editing and self.instance.device:
            # When editing, include current device even if it's assigned
            available_devices = Device.objects.filter(
                Q(status='AVAILABLE', is_active=True) |
                Q(id=self.instance.device.id)
            ).select_related('subcategory__category').order_by('device_id')
        else:
            # For new assignments, only show available devices
            available_devices = Device.objects.filter(
                status='AVAILABLE',
                is_active=True
            ).select_related('subcategory__category').order_by('device_id')
        
        self.fields['device'].queryset = available_devices
        self.fields['device'].empty_label = "Select an available device..."
        
        # Filter users - only active Parliament employees
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True,
            is_active_employee=True
        ).order_by('first_name', 'last_name')
        self.fields['assigned_to'].empty_label = "Select employee..."
        
        # Filter locations - only active locations
        self.fields['assigned_location'].queryset = Location.objects.filter(
            is_active=True
        ).order_by('name')
        self.fields['assigned_location'].empty_label = "Select location (optional)..."
        
        # Set defaults for new assignments
        if not self.editing:
            self.fields['assigned_date'].initial = date.today()
            self.fields['assignment_type'].initial = 'TEMPORARY'
            self.fields['condition_at_assignment'].initial = 'GOOD'
        
        # Set help texts
        self._set_help_texts()
        
        # Handle assignment type dependent fields
        self._setup_conditional_fields()
    
    def _set_help_texts(self):
        """Set comprehensive help texts for form fields."""
        self.fields['device'].help_text = "Select device to assign. Only available devices are shown."
        self.fields['assigned_to'].help_text = "Parliament employee receiving the device"
        self.fields['assigned_location'].help_text = "Where the device will be used (optional)"
        self.fields['assignment_type'].help_text = "Type of assignment - affects return date requirements"
        self.fields['assigned_date'].help_text = "Date when device is assigned to user"
        self.fields['expected_return_date'].help_text = "Expected return date (required for temporary assignments)"
        self.fields['purpose'].help_text = "Brief description of why device is being assigned"
        self.fields['condition_at_assignment'].help_text = "Current condition of device being assigned"
        self.fields['emergency_contact'].help_text = "Emergency contact person in case device is lost/damaged"
        self.fields['emergency_phone'].help_text = "Emergency contact phone number"
    
    def _setup_conditional_fields(self):
        """Setup conditional field requirements based on assignment type."""
        # Add CSS classes for JavaScript handling
        self.fields['assignment_type'].widget.attrs['data-toggle'] = 'assignment-type'
        self.fields['expected_return_date'].widget.attrs['data-conditional'] = 'temporary'
        
        # Mark required fields visually
        required_fields = ['device', 'assigned_to', 'assignment_type', 'assigned_date', 'purpose']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['required'] = True
    
    def clean_device(self):
        """Validate device availability for assignment."""
        device = self.cleaned_data.get('device')
        
        if not device:
            raise ValidationError("Device selection is required.")
        
        # Check if device is available (unless editing same assignment)
        if device.status != 'AVAILABLE':
            if not self.editing or (self.editing and device != self.instance.device):
                raise ValidationError(
                    f"Device {device.device_id} is not available for assignment. "
                    f"Current status: {device.get_status_display()}"
                )
        
        # Check for existing active assignments (unless editing same assignment)
        existing_assignment = Assignment.objects.filter(
            device=device,
            status='ASSIGNED',
            is_active=True
        )
        
        if self.editing:
            existing_assignment = existing_assignment.exclude(id=self.instance.id)
        
        if existing_assignment.exists():
            assignment = existing_assignment.first()
            raise ValidationError(
                f"Device {device.device_id} is already assigned to "
                f"{assignment.assigned_to.get_full_name()} since {assignment.assigned_date}"
            )
        
        return device
    
    def clean_assigned_to(self):
        """Validate assigned user."""
        assigned_to = self.cleaned_data.get('assigned_to')
        
        if not assigned_to:
            raise ValidationError("Employee selection is required.")
        
        if not assigned_to.is_active:
            raise ValidationError("Selected employee is not active.")
        
        if not getattr(assigned_to, 'is_active_employee', True):
            raise ValidationError("Selected user is not an active Parliament employee.")
        
        return assigned_to
    
    def clean_assigned_date(self):
        """Validate assignment date."""
        assigned_date = self.cleaned_data.get('assigned_date')
        
        if not assigned_date:
            raise ValidationError("Assignment date is required.")
        
        # Check if date is not too far in the past (unless editing)
        if not self.editing:
            thirty_days_ago = date.today() - timedelta(days=30)
            if assigned_date < thirty_days_ago:
                raise ValidationError("Assignment date cannot be more than 30 days in the past.")
        
        # Check if date is not too far in the future
        ninety_days_future = date.today() + timedelta(days=90)
        if assigned_date > ninety_days_future:
            raise ValidationError("Assignment date cannot be more than 90 days in the future.")
        
        return assigned_date
    
    def clean_expected_return_date(self):
        """Validate expected return date based on assignment type."""
        expected_return_date = self.cleaned_data.get('expected_return_date')
        assignment_type = self.cleaned_data.get('assignment_type')
        assigned_date = self.cleaned_data.get('assigned_date')
        
        # Required for temporary assignments
        if assignment_type == 'TEMPORARY' and not expected_return_date:
            raise ValidationError("Expected return date is required for temporary assignments.")
        
        # Validate return date is after assignment date
        if expected_return_date and assigned_date:
            if expected_return_date <= assigned_date:
                raise ValidationError("Expected return date must be after assignment date.")
            
            # Check reasonable timeframe
            max_days = 365 * 2  # 2 years maximum
            if (expected_return_date - assigned_date).days > max_days:
                raise ValidationError("Assignment period cannot exceed 2 years.")
        
        return expected_return_date
    
    def clean_purpose(self):
        """Validate purpose field."""
        purpose = self.cleaned_data.get('purpose')
        
        if not purpose or not purpose.strip():
            raise ValidationError("Assignment purpose is required.")
        
        if len(purpose.strip()) < 5:
            raise ValidationError("Purpose must be at least 5 characters long.")
        
        return purpose.strip()
    
    def clean_emergency_phone(self):
        """Validate emergency phone number format."""
        emergency_phone = self.cleaned_data.get('emergency_phone')
        
        if emergency_phone:
            # Remove spaces and dashes for validation
            phone_digits = ''.join(c for c in emergency_phone if c.isdigit())
            
            # Bangladesh phone number validation
            if len(phone_digits) < 11 or len(phone_digits) > 14:
                raise ValidationError("Please enter a valid phone number (11-14 digits).")
            
            # Check if starts with valid BD mobile prefixes
            if len(phone_digits) == 11 and not phone_digits.startswith(('013', '014', '015', '016', '017', '018', '019')):
                raise ValidationError("Please enter a valid Bangladesh mobile number.")
        
        return emergency_phone
    
    def clean(self):
        """Perform cross-field validation."""
        cleaned_data = super().clean()
        
        assignment_type = cleaned_data.get('assignment_type')
        expected_return_date = cleaned_data.get('expected_return_date')
        
        # Permanent assignments should not have return dates
        if assignment_type == 'PERMANENT' and expected_return_date:
            cleaned_data['expected_return_date'] = None
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save assignment with additional logic."""
        assignment = super().save(commit=False)
        
        # Set assigned_by if user is provided
        if self.user:
            assignment.assigned_by = self.user
        
        # Set status for new assignments
        if not self.editing:
            assignment.status = 'ASSIGNED'
            assignment.is_active = True
        
        if commit:
            assignment.save()
        
        return assignment


class QuickAssignmentForm(forms.ModelForm):
    """
    Simplified form for quick device assignments.
    Contains only essential fields for fast assignment workflow.
    """
    
    class Meta:
        model = Assignment
        fields = [
            'device', 'assigned_to', 'assignment_type',
            'assigned_date', 'expected_return_date', 'purpose'
        ]
        
        widgets = {
            'device': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'assignment_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'assigned_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'expected_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Assignment purpose...',
                'required': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter to available devices only
        self.fields['device'].queryset = Device.objects.filter(
            status='AVAILABLE',
            is_active=True
        ).order_by('device_id')
        
        # Filter to active employees only
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True,
            is_active_employee=True
        ).order_by('first_name', 'last_name')
        
        # Set defaults
        self.fields['assigned_date'].initial = date.today()
        self.fields['assignment_type'].initial = 'TEMPORARY'


class AssignmentFilterForm(forms.Form):
    """
    Form for filtering assignments with multiple criteria.
    Used in assignment list views for search and filtering.
    """
    
    # Search fields
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control search-input',
            'placeholder': 'Search by assignment ID, device ID, or employee name...',
            'autocomplete': 'off'
        }),
        help_text="Search assignments by ID, device, or employee"
    )
    
    # Status filter
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Assignment.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select filter-dropdown'
        })
    )
    
    # Assignment type filter
    assignment_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Assignment.ASSIGNMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select filter-dropdown'
        })
    )
    
    # Employee filter
    assigned_to = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True),
        empty_label="All Employees",
        widget=forms.Select(attrs={
            'class': 'form-select filter-dropdown employee-filter'
        })
    )
    
    # Location filter
    assigned_location = forms.ModelChoiceField(
        required=False,
        queryset=Location.objects.filter(is_active=True),
        empty_label="All Locations",
        widget=forms.Select(attrs={
            'class': 'form-select filter-dropdown location-filter'
        })
    )
    
    # Date range filters
    assigned_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control date-picker',
            'type': 'date',
            'placeholder': 'From date'
        })
    )
    
    assigned_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control date-picker',
            'type': 'date',
            'placeholder': 'To date'
        })
    )
    
    # Return date filters
    expected_return_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control date-picker',
            'type': 'date'
        })
    )
    
    expected_return_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control date-picker',
            'type': 'date'
        })
    )
    
    # Overdue filter
    is_overdue = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Assignments'),
            ('yes', 'Overdue Only'),
            ('no', 'Not Overdue'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select filter-dropdown'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Order employee choices
        self.fields['assigned_to'].queryset = self.fields['assigned_to'].queryset.order_by(
            'first_name', 'last_name'
        )
        
        # Order location choices
        self.fields['assigned_location'].queryset = self.fields['assigned_location'].queryset.order_by('name')
    
    def clean(self):
        """Validate date ranges."""
        cleaned_data = super().clean()
        
        # Validate assigned date range
        assigned_from = cleaned_data.get('assigned_date_from')
        assigned_to = cleaned_data.get('assigned_date_to')
        
        if assigned_from and assigned_to and assigned_to < assigned_from:
            raise ValidationError("Assignment end date must be after start date.")
        
        # Validate return date range
        return_from = cleaned_data.get('expected_return_date_from')
        return_to = cleaned_data.get('expected_return_date_to')
        
        if return_from and return_to and return_to < return_from:
            raise ValidationError("Return end date must be after start date.")
        
        return cleaned_data


class AssignmentReturnForm(forms.ModelForm):
    """
    Form for handling device returns and assignment completion.
    """
    
    class Meta:
        model = Assignment
        fields = [
            'actual_return_date', 'condition_at_return',
            'return_notes'
        ]
        
        widgets = {
            'actual_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'condition_at_return': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'return_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Notes about device return, condition, or any issues...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default return date to today
        self.fields['actual_return_date'].initial = date.today()
            
        # Set help texts
        self.fields['actual_return_date'].help_text = "Date when device was actually returned"
        self.fields['condition_at_return'].help_text = "Condition of device upon return"
        self.fields['return_notes'].help_text = "Any notes about the return process or device condition"
    
    def clean_actual_return_date(self):
        """Validate return date."""
        return_date = self.cleaned_data.get('actual_return_date')
        
        if not return_date:
            raise ValidationError("Return date is required.")
        
        if self.instance and self.instance.assigned_date:
            if return_date < self.instance.assigned_date:
                raise ValidationError("Return date cannot be before assignment date.")
        
        if return_date > date.today():
            raise ValidationError("Return date cannot be in the future.")
        
        return return_date
    
    def save(self, commit=True):
        """Save return with status update."""
        assignment = super().save(commit=False)
        assignment.status = 'RETURNED'
        assignment.is_active = False
        
        if commit:
            assignment.save()
        
        return assignment


class AssignmentTransferForm(forms.Form):
    """
    Form for transferring assignments between users or locations.
    """
    
    new_assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label="Keep current employee",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select new employee (leave blank to keep current)"
    )
    
    new_assigned_location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_active=True),
        required=False,
        empty_label="Keep current location",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select new location (leave blank to keep current)"
    )
    
    transfer_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for transfer...',
            'required': True
        }),
        help_text="Explain why this transfer is being made"
    )
    
    effective_date = forms.DateField(
        initial=date.today,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'required': True
        }),
        help_text="Date when transfer takes effect"
    )
    
    def __init__(self, assignment=None, *args, **kwargs):
        self.assignment = assignment
        super().__init__(*args, **kwargs)
        
        if assignment:
            # Exclude current assignee from new employee options
            self.fields['new_assigned_to'].queryset = self.fields['new_assigned_to'].queryset.exclude(
                id=assignment.assigned_to.id
            )
    
    def clean(self):
        """Validate transfer details."""
        cleaned_data = super().clean()
        
        new_assigned_to = cleaned_data.get('new_assigned_to')
        new_assigned_location = cleaned_data.get('new_assigned_location')
        
        # At least one field must be changed
        if not new_assigned_to and not new_assigned_location:
            raise ValidationError("At least one field (employee or location) must be changed for transfer.")
        
        # Validate effective date
        effective_date = cleaned_data.get('effective_date')
        if effective_date:
            if self.assignment and effective_date < self.assignment.assigned_date:
                raise ValidationError("Transfer effective date cannot be before original assignment date.")
            
            if effective_date > date.today() + timedelta(days=30):
                raise ValidationError("Transfer effective date cannot be more than 30 days in the future.")
        
        return cleaned_data