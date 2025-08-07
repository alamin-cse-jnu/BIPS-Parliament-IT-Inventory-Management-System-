"""
Forms for Devices app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines forms for device management including:
- DeviceCategoryForm: Create and edit device categories
- DeviceSubcategoryForm: Create and edit device subcategories
- DeviceForm: Create and edit devices with JSON specifications
- DeviceFilterForm: Filter devices by various criteria
- DeviceSearchForm: Search devices
- WarrantyForm: Create and edit warranties
- DeviceBulkUpdateForm: Bulk update device properties

Features:
- Interactive JSON specifications with examples
- Dynamic filtering and search
- User-friendly validation and error handling
- Bootstrap 5.3 styling
- Real-time form validation
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta
import json

from .models import DeviceCategory, DeviceSubcategory, Device, Warranty, QRCode
from vendors.models import Vendor
from locations.models import Location
from users.models import CustomUser


class JSONSpecificationsWidget(forms.Textarea):
    """
    Custom widget for JSON specifications with interactive examples and validation.
    """
    
    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs', {})
        attrs.update({
            'class': 'form-control json-specifications-editor',
            'rows': 8,
            'style': 'font-family: monospace; font-size: 13px; line-height: 1.4;',
            'data-bs-toggle': 'tooltip',
            'data-bs-placement': 'top',
            'title': 'Enter specifications in JSON format. Click examples below for help.',
            'placeholder': 'Enter device specifications in JSON format...'
        })
        super().__init__(*args, **kwargs)
    
    def format_value(self, value):
        """Format JSON value for display."""
        if value is None or value == '':
            return ''
        if isinstance(value, dict):
            try:
                return json.dumps(value, indent=2, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(value)
        return value


class DeviceCategoryForm(forms.ModelForm):
    """Form for creating and editing device categories."""
    
    class Meta:
        model = DeviceCategory
        fields = ['name', 'code', 'description', 'icon_class', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name (e.g., Computers, Storage)',
                'maxlength': 100
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter short code (e.g., COMP, STOR)',
                'maxlength': 10,
                'style': 'text-transform: uppercase;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter detailed description of this category',
                'rows': 3
            }),
            'icon_class': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bootstrap icon class (e.g., bi-laptop, bi-router)',
                'maxlength': 50
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 999
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_code(self):
        """Validate and format category code."""
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper().strip()
            # Check for duplicate codes
            existing = DeviceCategory.objects.filter(code=code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(f"Category code '{code}' already exists.")
        return code
    
    def clean_name(self):
        """Validate category name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            # Check for duplicate names
            existing = DeviceCategory.objects.filter(name__iexact=name)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(f"Category name '{name}' already exists.")
        return name


class DeviceSubcategoryForm(forms.ModelForm):
    """Form for creating and editing device subcategories."""
    
    class Meta:
        model = DeviceSubcategory
        fields = ['category', 'name', 'code', 'description', 'sort_order', 'is_active']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter subcategory name (e.g., Laptops, Desktop)',
                'maxlength': 100
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter short code (e.g., LAP, DESK)',
                'maxlength': 15,
                'style': 'text-transform: uppercase;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter detailed description',
                'rows': 3
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 999
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields['category'].queryset = DeviceCategory.objects.filter(is_active=True)
    
    def clean_code(self):
        """Validate subcategory code uniqueness within category."""
        code = self.cleaned_data.get('code')
        category = self.cleaned_data.get('category')
        
        if code and category:
            code = code.upper().strip()
            # Check for duplicate codes within the same category
            existing = DeviceSubcategory.objects.filter(category=category, code=code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(f"Subcategory code '{code}' already exists in {category.name}.")
        return code


class DeviceForm(forms.ModelForm):
    """
    Comprehensive form for creating and editing devices with JSON specifications.
    """
    
    specifications_json = forms.CharField(
        widget=JSONSpecificationsWidget,
        required=False,
        help_text="Enter device specifications in JSON format. See examples below.",
        label="Specifications"
    )
    
    class Meta:
        model = Device
        fields = [
            'subcategory', 'device_type', 'parent_device',
            'brand', 'model', 'serial_number', 'asset_tag',
            'status', 'condition', 'priority',
            'purchase_date', 'purchase_price', 'vendor',
            'current_location', 'specifications_json',
            'notes', 'barcode', 'depreciation_rate',
            'is_active', 'is_assignable', 'requires_approval'
        ]
        widgets = {
            'subcategory': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'device_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_device_type'
            }),
            'parent_device': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true',
                'id': 'id_parent_device'
            }),
            'brand': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter brand name (e.g., Dell, HP, Cisco)',
                'maxlength': 100
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter model name/number',
                'maxlength': 150
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manufacturer serial number',
                'maxlength': 100
            }),
            'asset_tag': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter internal asset tag (optional)',
                'maxlength': 50
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'condition': forms.Select(attrs={
                'class': 'form-select'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': date.today().isoformat()
            }),
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price in BDT',
                'min': '0.01',
                'step': '0.01'
            }),
            'vendor': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'current_location': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter additional notes (optional)',
                'rows': 3
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter barcode (optional)',
                'maxlength': 100
            }),
            'depreciation_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_assignable': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_approval': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up querysets
        self.fields['subcategory'].queryset = DeviceSubcategory.objects.filter(
            is_active=True
        ).select_related('category').order_by('category__name', 'name')
        
        self.fields['vendor'].queryset = Vendor.objects.filter(
            is_active=True
        ).order_by('name')
        
        self.fields['current_location'].queryset = Location.objects.all().order_by('name')
        
        # Set parent device choices (only complete devices)
        self.fields['parent_device'].queryset = Device.objects.filter(
            device_type='COMPLETE',
            is_active=True
        ).order_by('device_id')
        
        # Initialize specifications field
        if self.instance.pk and self.instance.specifications:
            self.fields['specifications_json'].initial = json.dumps(
                self.instance.specifications, indent=2, ensure_ascii=False
            )
        
        # Customize field labels and help texts
        self.fields['specifications_json'].help_text = """
        Enter specifications in JSON format. Examples:
        • Desktop: {"cpu": "Intel i5", "ram": "16GB DDR4", "storage": "512GB SSD"}
        • Router: {"ports": "24 Gigabit", "wifi": "802.11ac", "throughput": "100 Mbps"}
        • RAM: {"size": "8GB", "type": "DDR4", "speed": "3200MHz"}
        """
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if not field.widget.attrs.get('class'):
                if isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-check-input'
                elif isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'
    
    def clean_specifications_json(self):
        """Validate JSON specifications."""
        specifications_json = self.cleaned_data.get('specifications_json', '')
        
        if not specifications_json.strip():
            return {}
        
        try:
            parsed = json.loads(specifications_json)
            if not isinstance(parsed, dict):
                raise ValidationError("Specifications must be a JSON object (dictionary)")
            return parsed
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {str(e)}")
    
    def clean(self):
        """Additional validation."""
        cleaned_data = super().clean()
        device_type = cleaned_data.get('device_type')
        parent_device = cleaned_data.get('parent_device')
        status = cleaned_data.get('status')
        condition = cleaned_data.get('condition')
        is_assignable = cleaned_data.get('is_assignable')
        
        # Validate parent device relationship
        if parent_device and device_type == 'COMPLETE':
            raise ValidationError({
                'parent_device': "Complete devices cannot have parent devices"
            })
        
        if parent_device and parent_device.device_type != 'COMPLETE':
            raise ValidationError({
                'parent_device': "Parent device must be a complete device"
            })
        
        # Business logic validation
        if status == 'ASSIGNED' and not is_assignable:
            raise ValidationError({
                'status': "Device marked as non-assignable cannot be assigned"
            })
        
        if condition == 'DAMAGED' and status == 'AVAILABLE':
            raise ValidationError({
                'status': "Damaged devices should not be available for assignment"
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save device with JSON specifications."""
        device = super().save(commit=False)
        
        # Set specifications from JSON field
        specifications_json = self.cleaned_data.get('specifications_json', {})
        device.specifications = specifications_json
        
        if commit:
            device.save()
        
        return device


class DeviceFilterForm(forms.Form):
    """Form for filtering devices by various criteria."""
    
    category = forms.ModelChoiceField(
        queryset=DeviceCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    subcategory = forms.ModelChoiceField(
        queryset=DeviceSubcategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Subcategories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    device_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Device.DEVICE_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Device.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    condition = forms.ChoiceField(
        choices=[('', 'All Conditions')] + Device.CONDITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.filter(is_active=True),
        required=False,
        empty_label="All Vendors",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        empty_label="All Locations",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    purchase_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Purchase Date From"
    )
    
    purchase_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Purchase Date To"
    )
    
    is_assignable = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Assignable'), ('false', 'Non-assignable')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assignability"
    )
    
    warranty_status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('under_warranty', 'Under Warranty'),
            ('expires_soon', 'Expires Soon'),
            ('no_warranty', 'No Warranty')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Warranty Status"
    )


class DeviceSearchForm(forms.Form):
    """Simple search form for devices."""
    
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search devices by ID, brand, model, serial number...',
            'autocomplete': 'off'
        }),
        label=""
    )
    
    def search(self, queryset):
        """Apply search filters to queryset."""
        query = self.cleaned_data.get('query')
        
        if query:
            # Split query into words for better matching
            words = query.split()
            q_objects = Q()
            
            for word in words:
                q_objects |= (
                    Q(device_id__icontains=word) |
                    Q(brand__icontains=word) |
                    Q(model__icontains=word) |
                    Q(serial_number__icontains=word) |
                    Q(asset_tag__icontains=word) |
                    Q(notes__icontains=word)
                )
            
            queryset = queryset.filter(q_objects)
        
        return queryset


class WarrantyForm(forms.ModelForm):
    """Form for creating and editing warranties."""
    
    class Meta:
        model = Warranty
        fields = [
            'device', 'warranty_type', 'provider',
            'warranty_number', 'start_date', 'end_date',
            'coverage_description', 'terms_conditions',
            'contact_person', 'contact_phone', 'contact_email',
            'is_active'
        ]
        widgets = {
            'device': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'warranty_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'provider': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'warranty_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter warranty reference number',
                'maxlength': 100
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'coverage_description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe what is covered by this warranty',
                'rows': 4
            }),
            'terms_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter terms and conditions (optional)',
                'rows': 3
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact person name',
                'maxlength': 100
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact phone number',
                'maxlength': 20
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact email address'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up querysets
        self.fields['device'].queryset = Device.objects.filter(
            is_active=True
        ).order_by('device_id')
        
        self.fields['provider'].queryset = Vendor.objects.filter(
            is_active=True
        ).order_by('name')
    
    def clean(self):
        """Validate warranty dates."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError({
                    'end_date': "End date must be after start date"
                })
            
            # Check if dates are reasonable
            if start_date > date.today() + timedelta(days=365):
                raise ValidationError({
                    'start_date': "Start date seems too far in the future"
                })
        
        return cleaned_data


class DeviceBulkUpdateForm(forms.Form):
    """Form for bulk updating device properties."""
    
    BULK_ACTIONS = [
        ('', 'Select Action'),
        ('update_status', 'Update Status'),
        ('update_condition', 'Update Condition'),
        ('update_location', 'Update Location'),
        ('update_assignability', 'Update Assignability'),
    ]
    
    action = forms.ChoiceField(
        choices=BULK_ACTIONS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Status update fields
    new_status = forms.ChoiceField(
        choices=Device.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Condition update fields
    new_condition = forms.ChoiceField(
        choices=Device.CONDITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Location update fields
    new_location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Assignability update fields
    new_assignability = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up location queryset
        self.fields['new_location'].queryset = Location.objects.all().order_by('name')