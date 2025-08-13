"""
Forms for Maintenance app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines forms for maintenance management, scheduling, and reporting
with enhanced validation and user-friendly interfaces.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import Maintenance
from devices.models import Device, DeviceCategory
from vendors.models import Vendor

User = get_user_model()


class MaintenanceBaseForm(forms.ModelForm):
    """
    Base form for maintenance with common styling and validation.
    """
    class Meta:
        model = Maintenance
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'min': str(date.today())
            }),
            'expected_end_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'min': str(date.today())
            }),
            'actual_start_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'actual_end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'follow_up_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'next_maintenance_due': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'approved_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter maintenance title (e.g., Quarterly Server Maintenance)',
                'maxlength': 200
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed description of maintenance work required...'
            }),
            'problem_reported': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description of the reported problem or issue...'
            }),
            'work_performed': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed description of work performed...'
            }),
            'parts_replaced': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'List of parts/components replaced...'
            }),
            'result_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes about maintenance result...'
            }),
            'internal_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Internal notes for IT team (not visible to users)...'
            }),
            'technician_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of primary technician'
            }),
            'technician_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+880XXXXXXXXX',
                'pattern': r'^\+?880\d{10}$'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'actual_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'parts_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'labor_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'downtime_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.25',
                'min': '0'
            }),
            'satisfaction_rating': forms.Select(attrs={
                'class': 'form-select'
            }, choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]),
            'maintenance_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'provider_type': forms.Select(attrs={'class': 'form-select'}),
            'result': forms.Select(attrs={'class': 'form-select'}),
            'device': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'vendor': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'approved_by': forms.Select(attrs={
                'class': 'form-select',
                'readonly': 'readonly'
            }),
            'requires_approval': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'follow_up_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_warranty_service': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter querysets for better performance and relevance
        self._setup_querysets()
        
        # Customize field requirements based on status
        self._setup_field_requirements()
        
        # Add help texts
        self._add_help_texts()
        
        # Hide internal notes for users without permission
        if self.user and not self.user.has_perm('maintenance.view_internal_notes'):
            if 'internal_notes' in self.fields:
                self.fields['internal_notes'].widget = forms.HiddenInput()
    
    def _setup_querysets(self):
        """Setup optimized querysets for foreign key fields."""
        # Only show active devices
        if 'device' in self.fields:
            self.fields['device'].queryset = Device.objects.filter(
                is_active=True
            ).select_related('subcategory__category').order_by('device_id')
        
        # Only show active vendors with maintenance services
        if 'vendor' in self.fields:
            self.fields['vendor'].queryset = Vendor.objects.filter(
                is_active=True,
                vendor_type__in=['SUPPLIER', 'SERVICE_PROVIDER', 'BOTH']
            ).order_by('name')
        
        # Only show staff users for approval
        if 'approved_by' in self.fields:
            self.fields['approved_by'].queryset = User.objects.filter(
                is_active=True,
                is_staff=True
            ).order_by('first_name', 'last_name')
    
    def _setup_field_requirements(self):
        """Setup field requirements based on maintenance status."""
        if self.instance and self.instance.pk:
            status = self.instance.status
            
            # Make fields required for completed maintenance
            if status == 'COMPLETED':
                self.fields['work_performed'].required = True
                self.fields['result'].required = True
                self.fields['actual_cost'].required = True
            
            # Make vendor required for external provider type
            if self.instance.provider_type == 'VENDOR':
                self.fields['vendor'].required = True
    
    def _add_help_texts(self):
        """Add helpful text for complex fields."""
        self.fields['estimated_cost'].help_text = "Estimated cost in BDT (Bangladeshi Taka)"
        self.fields['actual_cost'].help_text = "Final cost in BDT (required when maintenance is completed)"
        self.fields['downtime_hours'].help_text = "Total device downtime in hours"
        self.fields['satisfaction_rating'].help_text = "Rate the service quality (1=Poor, 5=Excellent)"
        self.fields['requires_approval'].help_text = "Check if this maintenance requires management approval"
        self.fields['is_warranty_service'].help_text = "Check if this maintenance is covered under warranty"
    
    def clean(self):
        """Perform cross-field validation."""
        cleaned_data = super().clean()
        
        # Date validations
        self._validate_dates(cleaned_data)
        
        # Cost validations
        self._validate_costs(cleaned_data)
        
        # Status-specific validations
        self._validate_status_requirements(cleaned_data)
        
        # Provider validations
        self._validate_provider_requirements(cleaned_data)
        
        return cleaned_data
    
    def _validate_dates(self, cleaned_data):
        """Validate date fields."""
        start_date = cleaned_data.get('start_date')
        expected_end_date = cleaned_data.get('expected_end_date')
        actual_start_date = cleaned_data.get('actual_start_date')
        actual_end_date = cleaned_data.get('actual_end_date')
        follow_up_date = cleaned_data.get('follow_up_date')
        
        # Start date must be before expected end date
        if start_date and expected_end_date:
            if start_date >= expected_end_date:
                raise ValidationError({
                    'expected_end_date': 'Expected end date must be after start date.'
                })
        
        # Actual dates validation
        if actual_start_date and actual_end_date:
            if actual_start_date >= actual_end_date:
                raise ValidationError({
                    'actual_end_date': 'Actual end date must be after actual start date.'
                })
        
        # Follow-up date should be in the future
        if follow_up_date and follow_up_date <= timezone.now().date():
            raise ValidationError({
                'follow_up_date': 'Follow-up date should be in the future.'
            })
        
        # Start date should not be too far in the past (for new records)
        if not self.instance.pk and start_date:
            max_past_days = 30
            if start_date < timezone.now().date() - timedelta(days=max_past_days):
                raise ValidationError({
                    'start_date': f'Start date cannot be more than {max_past_days} days in the past.'
                })
    
    def _validate_costs(self, cleaned_data):
        """Validate cost fields."""
        estimated_cost = cleaned_data.get('estimated_cost')
        actual_cost = cleaned_data.get('actual_cost')
        parts_cost = cleaned_data.get('parts_cost')
        labor_cost = cleaned_data.get('labor_cost')
        
        # Warn if actual cost significantly exceeds estimated cost
        if estimated_cost and actual_cost:
            variance_threshold = Decimal('0.5')  # 50%
            if actual_cost > estimated_cost * (1 + variance_threshold):
                self.add_error('actual_cost', 
                    f'Actual cost is {((actual_cost / estimated_cost - 1) * 100):.1f}% '
                    f'higher than estimated. Please verify the amount.')
        
        # Validate parts and labor cost sum
        if parts_cost and labor_cost and actual_cost and actual_cost != (parts_cost + labor_cost):
            self.add_error('actual_cost', 'Actual cost does not match the sum of parts and labor costs.')
    
    def _validate_status_requirements(self, cleaned_data):
        """Validate requirements based on status."""
        status = cleaned_data.get('status')
        
        if status == 'COMPLETED':
            required_fields = ['work_performed', 'result']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for completed maintenance.')
        
        if status == 'IN_PROGRESS' and not cleaned_data.get('actual_start_date'):
            cleaned_data['actual_start_date'] = timezone.now()
    
    def _validate_provider_requirements(self, cleaned_data):
        """Validate provider-specific requirements."""
        provider_type = cleaned_data.get('provider_type')
        vendor = cleaned_data.get('vendor')
        
        if provider_type == 'VENDOR' and not vendor:
            self.add_error('vendor', 'Vendor must be selected when provider type is "External Vendor".')
        
        if provider_type == 'INTERNAL' and vendor:
            self.add_error('vendor', 'Vendor should not be selected for internal maintenance.')


class MaintenanceCreateForm(MaintenanceBaseForm):
    """
    Form for creating new maintenance records.
    """
    class Meta(MaintenanceBaseForm.Meta):
        exclude = [
            'maintenance_id', 'uuid', 'actual_start_date', 'actual_end_date',
            'approved_by', 'approved_at', 'created_by', 'updated_by',
            'created_at', 'updated_at'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set defaults for new maintenance
        self.fields['status'].initial = 'SCHEDULED'
        self.fields['priority'].initial = 'MEDIUM'
        self.fields['maintenance_type'].initial = 'PREVENTIVE'
        self.fields['provider_type'].initial = 'INTERNAL'
        self.fields['is_active'].initial = True
        
        # Hide advanced fields for creation
        advanced_fields = [
            'work_performed', 'parts_replaced', 'result', 'result_notes',
            'satisfaction_rating', 'downtime_hours', 'internal_notes'
        ]
        for field in advanced_fields:
            if field in self.fields:
                self.fields[field].widget = forms.HiddenInput()
        
        # Set minimum dates
        today = timezone.now().date()
        self.fields['start_date'].widget.attrs['min'] = str(today)
        self.fields['expected_end_date'].widget.attrs['min'] = str(today + timedelta(days=1))
    
    def clean_device(self):
        """Validate device can be assigned for maintenance."""
        device = self.cleaned_data.get('device')
        
        if device:
            # Check if device has conflicting active maintenance
            conflicting_maintenance = Maintenance.objects.filter(
                device=device,
                status__in=['SCHEDULED', 'IN_PROGRESS'],
                is_active=True
            )
            
            if self.instance.pk:
                conflicting_maintenance = conflicting_maintenance.exclude(pk=self.instance.pk)
            
            if conflicting_maintenance.exists():
                maintenance = conflicting_maintenance.first()
                raise ValidationError(
                    f'Device already has active maintenance: {maintenance.maintenance_id} '
                    f'({maintenance.get_status_display()})'
                )
            
            # Check device status
            if device.status == 'RETIRED':
                raise ValidationError('Cannot schedule maintenance for retired devices.')
            
            if device.status == 'LOST':
                raise ValidationError('Cannot schedule maintenance for lost devices.')
        
        return device


class MaintenanceUpdateForm(MaintenanceBaseForm):
    """
    Form for updating existing maintenance records.
    """
    class Meta(MaintenanceBaseForm.Meta):
        exclude = ['maintenance_id', 'uuid', 'device', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make device field read-only after creation
        if self.instance and self.instance.pk:
            device_info = f"{self.instance.device.device_id} - {self.instance.device.brand} {self.instance.device.model}"
            self.fields['device_info'] = forms.CharField(
                label='Device',
                initial=device_info,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': 'readonly'
                }),
                required=False
            )
    
    def clean_status(self):
        """Validate status transitions."""
        new_status = self.cleaned_data.get('status')
        
        if self.instance and self.instance.pk:
            if not self.instance.can_transition_to(new_status):
                raise ValidationError(
                    f'Invalid status transition from {self.instance.status} to {new_status}.'
                )
        
        return new_status


class MaintenanceScheduleForm(forms.Form):
    """
    Form for scheduling preventive maintenance.
    """
    SCHEDULE_TYPES = [
        ('single', 'Single Maintenance'),
        ('recurring', 'Recurring Maintenance'),
    ]
    
    RECURRENCE_PATTERNS = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly (every 3 months)'),
        ('biannual', 'Bi-annual (every 6 months)'),
        ('annual', 'Annual (yearly)'),
        ('custom', 'Custom interval'),
    ]
    
    schedule_type = forms.ChoiceField(
        choices=SCHEDULE_TYPES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        help_text="Choose scheduling type"
    )
    
    devices = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text="Select devices for maintenance scheduling"
    )
    
    maintenance_type = forms.ChoiceField(
        choices=Maintenance.MAINTENANCE_TYPES,
        initial='PREVENTIVE',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Type of maintenance to schedule"
    )
    
    priority = forms.ChoiceField(
        choices=Maintenance.PRIORITY_CHOICES,
        initial='MEDIUM',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Priority level for scheduled maintenance"
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': str(timezone.now().date())
        }),
        help_text="First maintenance date"
    )
    
    duration_days = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '30'
        }),
        help_text="Expected duration in days"
    )
    
    recurrence_pattern = forms.ChoiceField(
        choices=RECURRENCE_PATTERNS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="How often to repeat (for recurring maintenance)"
    )
    
    custom_interval_days = forms.IntegerField(
        min_value=1,
        max_value=365,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '365'
        }),
        help_text="Custom interval in days"
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text="Last maintenance date (for recurring schedules)"
    )
    
    max_occurrences = forms.IntegerField(
        min_value=1,
        max_value=50,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '50'
        }),
        help_text="Maximum number of maintenance schedules to create"
    )
    
    description_template = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Description template for scheduled maintenance...'
        }),
        help_text="Template description (use {date} for maintenance date)"
    )
    
    estimated_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }),
        help_text="Estimated cost per maintenance (BDT)"
    )
    
    requires_approval = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Require approval for scheduled maintenance"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show active devices that can be maintained
        self.fields['devices'].queryset = Device.objects.filter(
            is_active=True,
            status__in=['AVAILABLE', 'ASSIGNED']
        ).select_related('subcategory__category').order_by('device_id')
        
        # Set default values
        self.fields['start_date'].initial = timezone.now().date() + timedelta(days=7)
    
    def clean(self):
        """Validate scheduling parameters."""
        cleaned_data = super().clean()
        
        schedule_type = cleaned_data.get('schedule_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        recurrence_pattern = cleaned_data.get('recurrence_pattern')
        custom_interval_days = cleaned_data.get('custom_interval_days')
        max_occurrences = cleaned_data.get('max_occurrences')
        
        # Recurring schedule validations
        if schedule_type == 'recurring':
            if not recurrence_pattern:
                raise ValidationError({
                    'recurrence_pattern': 'Recurrence pattern is required for recurring schedules.'
                })
            
            if recurrence_pattern == 'custom' and not custom_interval_days:
                raise ValidationError({
                    'custom_interval_days': 'Custom interval days are required when recurrence pattern is set to "Custom".'
                })
            
            if not end_date and not max_occurrences:
                raise ValidationError(
                    'Either end date or maximum occurrences must be specified for recurring schedules.'
                )
            
            if end_date and start_date and end_date <= start_date:
                raise ValidationError({
                    'end_date': 'End date must be after start date.'
                })
        
        return cleaned_data


class MaintenanceQuickActionForm(forms.Form):
    """
    Form for quick maintenance actions from device pages.
    """
    action_type = forms.ChoiceField(
        choices=[
            ('schedule', 'Schedule Maintenance'),
            ('report_issue', 'Report Issue'),
            ('mark_maintenance', 'Mark as Needing Maintenance'),
        ],
        widget=forms.HiddenInput()
    )
    
    maintenance_type = forms.ChoiceField(
        choices=Maintenance.MAINTENANCE_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    priority = forms.ChoiceField(
        choices=Maintenance.PRIORITY_CHOICES,
        initial='MEDIUM',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe the maintenance required or issue reported...'
        })
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': str(timezone.now().date())
        }),
        initial=timezone.now().date() + timedelta(days=1)
    )
    
    estimated_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.device = kwargs.pop('device', None)
        super().__init__(*args, **kwargs)
        
        # Customize based on action type
        action_type = self.initial.get('action_type', 'schedule')
        
        if action_type == 'report_issue':
            self.fields['maintenance_type'].initial = 'CORRECTIVE'
            self.fields['priority'].initial = 'HIGH'
            self.fields['description'].widget.attrs['placeholder'] = 'Describe the issue or problem...'
        
        elif action_type == 'mark_maintenance':
            self.fields['maintenance_type'].initial = 'PREVENTIVE'
            self.fields['start_date'].initial = timezone.now().date()
    
    def clean(self):
        """Validate device is provided."""
        cleaned_data = super().clean()
        if not self.device:
            raise ValidationError('Device must be specified for quick actions.')
        return cleaned_data


class MaintenanceFilterForm(forms.Form):
    """
    Simplified form for filtering maintenance lists.
    """
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Maintenance.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    maintenance_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Maintenance.MAINTENANCE_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        choices=[('', 'All Priorities')] + Maintenance.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_range = forms.ChoiceField(
        choices=[
            ('', 'All Time'),
            ('today', 'Today'),
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('quarter', 'This Quarter'),
            ('year', 'This Year'),
            ('overdue', 'Overdue'),
            ('due_soon', 'Due Soon'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search maintenance...',
            'autocomplete': 'off'
        })
    )


class MaintenanceApprovalForm(forms.ModelForm):
    """
    Form for approving maintenance requests.
    """
    approval_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter approval notes or comments...'
        }),
        required=False,
        help_text="Optional notes about the approval"
    )
    
    class Meta:
        model = Maintenance
        fields = ['approved_by', 'approved_at', 'approval_notes']
        widgets = {
            'approved_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'readonly': 'readonly'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set current user and time as defaults
        if self.user:
            self.fields['approved_by'].initial = self.user
            self.fields['approved_by'].widget.attrs['readonly'] = 'readonly'
        
        self.fields['approved_at'].initial = timezone.now()
    
    def clean(self):
        """Validate approval permissions."""
        cleaned_data = super().clean()
        
        if self.user and not self.user.has_perm('maintenance.approve_maintenance'):
            raise ValidationError('You do not have permission to approve maintenance.')
        
        return cleaned_data


class MaintenanceSearchForm(forms.Form):
    """
    Form for searching and filtering maintenance records.
    """
    search_query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by maintenance ID, device, description...',
            'autocomplete': 'off'
        }),
        help_text="Search in maintenance ID, device ID, title, description"
    )
    
    status = forms.MultipleChoiceField(
        choices=Maintenance.STATUS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text="Select one or more statuses"
    )
    
    maintenance_type = forms.MultipleChoiceField(
        choices=Maintenance.MAINTENANCE_TYPES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text="Select one or more maintenance types"
    )
    
    priority = forms.MultipleChoiceField(
        choices=Maintenance.PRIORITY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text="Select one or more priority levels"
    )
    
    start_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text="Maintenance start date from"
    )
    
    start_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text="Maintenance start date to"
    )
    
    cost_min = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }),
        help_text="Minimum cost (BDT)"
    )
    
    cost_max = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '999999.99',
            'step': '0.01',
            'min': '0'
        }),
        help_text="Maximum cost (BDT)"
    )
    
    vendor = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Vendors",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Filter by vendor"
    )
    
    device_category = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Filter by device category"
    )
    
    overdue_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Show only overdue maintenance"
    )
    
    warranty_service = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Show only warranty services"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup vendor choices
        self.fields['vendor'].queryset = Vendor.objects.filter(
            is_active=True
        ).order_by('name')
        
        # Setup device category choices
        categories = DeviceCategory.objects.filter(is_active=True).order_by('name')
        self.fields['device_category'].choices = [('', 'All Categories')] + [
            (cat.id, cat.name) for cat in categories
        ]
    
    def clean(self):
        """Validate search criteria."""
        cleaned_data = super().clean()
        
        start_date_from = cleaned_data.get('start_date_from')
        start_date_to = cleaned_data.get('start_date_to')
        cost_min = cleaned_data.get('cost_min')
        cost_max = cleaned_data.get('cost_max')
        
        # Date range validation
        if start_date_from and start_date_to:
            if start_date_from > start_date_to:
                raise ValidationError({
                    'start_date_to': 'End date must be after start date.'
                })
        
        # Cost range validation
        if cost_min and cost_max:
            if cost_min > cost_max:
                raise ValidationError({
                    'cost_max': 'Maximum cost must be greater than minimum cost.'
                })
        
        return cleaned_data


class MaintenanceReportForm(forms.Form):
    """
    Form for generating maintenance reports.
    """
    REPORT_TYPES = [
        ('summary', 'Maintenance Summary Report'),
        ('detailed', 'Detailed Maintenance Report'),
        ('cost_analysis', 'Cost Analysis Report'),
        ('performance', 'Performance Analysis Report'),
        ('overdue', 'Overdue Maintenance Report'),
        ('vendor_performance', 'Vendor Performance Report'),
    ]
    
    EXPORT_FORMATS = [
        ('pdf', 'PDF Document'),
        ('excel', 'Excel Spreadsheet'),
        ('csv', 'CSV File'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select the type of report to generate"
    )
    
    export_format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select the export format"
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text="Report period start date"
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text="Report period end date"
    )
    
    include_costs = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Include cost information in the report"
    )
    
    include_vendor_details = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Include vendor performance details"
    )
    
    group_by_category = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Group results by device category"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default date range (last 30 days)
        today = timezone.now().date()
        self.fields['date_from'].initial = today - timedelta(days=30)
        self.fields['date_to'].initial = today
    
    def clean(self):
        """Validate report parameters."""
        cleaned_data = super().clean()
        
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        report_type = cleaned_data.get('report_type')
        
        if date_from and date_to:
            if date_from > date_to:
                raise ValidationError({
                    'date_to': 'End date must be after start date.'
                })
            
            # Limit report range to prevent performance issues
            max_days = 365
            if (date_to - date_from).days > max_days:
                raise ValidationError(
                    f'Report period cannot exceed {max_days} days.'
                )
        
        if report_type in ['cost_analysis', 'vendor_performance'] and not cleaned_data.get('include_costs'):
            raise ValidationError({
                'include_costs': 'Cost information is required for cost analysis or vendor performance reports.'
            })
        
        return cleaned_data


class MaintenanceBulkUpdateForm(forms.Form):
    """
    Form for bulk updating maintenance records.
    """
    ACTION_CHOICES = [
        ('', 'Select Action'),
        ('mark_in_progress', 'Mark as In Progress'),
        ('mark_completed', 'Mark as Completed'),
        ('cancel', 'Cancel Maintenance'),
        ('update_priority', 'Update Priority'),
        ('assign_vendor', 'Assign Vendor'),
        ('set_approval', 'Set Approval Status'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': 'required'
        }),
        help_text="Select the action to perform on selected maintenance records"
    )
    
    new_priority = forms.ChoiceField(
        choices=[('', 'Select Priority')] + Maintenance.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="New priority level (for priority update action)"
    )
    
    new_vendor = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Select Vendor",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Vendor to assign (for vendor assignment action)"
    )
    
    approval_status = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Approval status (for approval action)"
    )
    
    bulk_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes for this bulk action...'
        }),
        required=False,
        help_text="Optional notes to add to all affected records"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup vendor choices
        self.fields['new_vendor'].queryset = Vendor.objects.filter(
            is_active=True,
            vendor_type__in=['SERVICE_PROVIDER', 'BOTH']
        ).order_by('name')
    
    def clean(self):
        """Validate bulk action requirements."""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        # Validate action-specific requirements
        if action == 'update_priority':
            if not cleaned_data.get('new_priority'):
                raise ValidationError({
                    'new_priority': 'Priority must be selected for priority update action.'
                })
        
        elif action == 'assign_vendor':
            if not cleaned_data.get('new_vendor'):
                raise ValidationError({
                    'new_vendor': 'Vendor must be selected for vendor assignment action.'
                })
        
        elif action == 'set_approval':
            if not self.user or not self.user.has_perm('maintenance.approve_maintenance'):
                raise ValidationError('You do not have permission to approve maintenance.')
        
        return cleaned_data


# Helper functions for form processing
def create_maintenance_schedule(form_data, user):
    """
    Create maintenance schedule(s) based on form data.
    """
    schedule_type = form_data['schedule_type']
    devices = form_data['devices']
    start_date = form_data['start_date']
    
    created_maintenance = []
    
    if schedule_type == 'single':
        # Create single maintenance for each device
        for device in devices:
            maintenance = Maintenance(
                device=device,
                maintenance_type=form_data['maintenance_type'],
                priority=form_data['priority'],
                start_date=start_date,
                expected_end_date=start_date + timedelta(days=form_data['duration_days']),
                title=f"{form_data['maintenance_type']} Maintenance - {device.device_id}",
                description=form_data['description_template'],
                estimated_cost=form_data.get('estimated_cost', 0),
                requires_approval=form_data.get('requires_approval', False),
                created_by=user
            )
            maintenance.save()
            created_maintenance.append(maintenance)
    
    else:  # recurring
        # Calculate recurrence interval
        interval_map = {
            'weekly': 7,
            'monthly': 30,
            'quarterly': 90,
            'biannual': 180,
            'annual': 365,
            'custom': form_data.get('custom_interval_days', 30)
        }
        
        interval = interval_map[form_data['recurrence_pattern']]
        end_date = form_data.get('end_date')
        max_occurrences = form_data.get('max_occurrences', 10)
        
        current_date = start_date
        occurrence_count = 0
        
        while occurrence_count < max_occurrences:
            if end_date and current_date > end_date:
                break
            
            for device in devices:
                maintenance = Maintenance(
                    device=device,
                    maintenance_type=form_data['maintenance_type'],
                    priority=form_data['priority'],
                    start_date=current_date,
                    expected_end_date=current_date + timedelta(days=form_data['duration_days']),
                    title=f"{form_data['maintenance_type']} Maintenance - {device.device_id}",
                    description=form_data['description_template'].replace('{date}', current_date.strftime('%Y-%m-%d')),
                    estimated_cost=form_data.get('estimated_cost', 0),
                    requires_approval=form_data.get('requires_approval', False),
                    created_by=user
                )
                maintenance.save()
                created_maintenance.append(maintenance)
            
            current_date += timedelta(days=interval)
            occurrence_count += 1
    
    return created_maintenance


def apply_bulk_maintenance_update(form_data, maintenance_queryset, user):
    """
    Apply bulk updates to maintenance records.
    """
    action = form_data['action']
    updated_count = 0
    
    for maintenance in maintenance_queryset:
        if action == 'mark_in_progress':
            if maintenance.can_be_started():
                maintenance.status = 'IN_PROGRESS'
                maintenance.actual_start_date = timezone.now()
                maintenance.updated_by = user
                maintenance.save()
                updated_count += 1
        
        elif action == 'mark_completed':
            if maintenance.can_be_completed():
                maintenance.status = 'COMPLETED'
                maintenance.actual_end_date = timezone.now()
                if not maintenance.result:
                    maintenance.result = 'SUCCESS'
                maintenance.updated_by = user
                maintenance.save()
                updated_count += 1
        
        elif action == 'cancel':
            if maintenance.can_be_cancelled():
                maintenance.status = 'CANCELLED'
                maintenance.updated_by = user
                maintenance.save()
                updated_count += 1
        
        elif action == 'update_priority':
            maintenance.priority = form_data['new_priority']
            maintenance.updated_by = user
            maintenance.save()
            updated_count += 1
        
        elif action == 'assign_vendor':
            maintenance.vendor = form_data['new_vendor']
            maintenance.provider_type = 'VENDOR'
            maintenance.updated_by = user
            maintenance.save()
            updated_count += 1
        
        elif action == 'set_approval':
            if user.has_perm('maintenance.approve_maintenance'):
                if form_data['approval_status']:
                    maintenance.approved_by = user
                    maintenance.approved_at = timezone.now()
                else:
                    maintenance.approved_by = None
                    maintenance.approved_at = None
                maintenance.updated_by = user
                maintenance.save()
                updated_count += 1
        
        # Add bulk notes if provided
        if form_data.get('bulk_notes'):
            if maintenance.internal_notes:
                maintenance.internal_notes += f"\n\n[Bulk Update {timezone.now().strftime('%Y-%m-%d %H:%M')}]: {form_data['bulk_notes']}"
            else:
                maintenance.internal_notes = f"[Bulk Update {timezone.now().strftime('%Y-%m-%d %H:%M')}]: {form_data['bulk_notes']}"
            maintenance.save()
    
    return updated_count