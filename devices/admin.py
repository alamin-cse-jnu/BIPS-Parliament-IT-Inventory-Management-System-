"""
Django Admin configuration for Devices app in PIMS
Bangladesh Parliament Secretariat

This module customizes the Django admin interface for device management models:
- DeviceCategory: Main categories with ordering and display optimization
- DeviceSubcategory: Subcategories with category filtering
- Device: Complete device management with JSON specifications editor
- Warranty: Warranty tracking with provider information
- QRCode: QR code management with preview capabilities

Features:
- Interactive JSON specifications editor
- Advanced filtering and search
- Inline editing for related models
- Custom actions for bulk operations
- Rich display formatting for better UX
"""

from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db import models
from django.forms import Textarea
from django.core.exceptions import ValidationError
import json

from .models import DeviceCategory, DeviceSubcategory, Device, Warranty, QRCode


# Custom Widgets
class JSONEditorWidget(forms.Textarea):
    """
    Custom widget for JSON field editing with better formatting.
    """
    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs', {})
        attrs.update({
            'class': 'json-editor',
            'rows': 10,
            'cols': 80,
            'style': 'font-family: monospace; font-size: 12px;',
            'placeholder': '''Enter specifications in JSON format. Examples:

Desktop/Laptop:
{
    "cpu": "Intel i5-12400",
    "ram": "16GB DDR4", 
    "storage": "512GB SSD",
    "monitor": "24 inch Dell"
}

Router:
{
    "ports": "24 Gigabit Ethernet",
    "wifi": "802.11ac",
    "throughput": "100 Mbps"
}

RAM Component:
{
    "size": "8GB",
    "type": "DDR4",
    "speed": "3200MHz"
}'''
        })
        super().__init__(*args, **kwargs)

    def format_value(self, value):
        """Format JSON value for display in textarea."""
        if value is None:
            return ''
        if isinstance(value, dict):
            try:
                return json.dumps(value, indent=2, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(value)
        return value


# Custom Forms
class DeviceAdminForm(forms.ModelForm):
    """
    Custom form for Device admin with enhanced validation and widgets.
    """
    
    class Meta:
        model = Device
        fields = '__all__'
        widgets = {
            'specifications': JSONEditorWidget,
            'notes': Textarea(attrs={'rows': 4, 'cols': 80}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Enhance field help texts
        self.fields['specifications'].help_text = """
        Enter device specifications in JSON format. You can add any fields relevant to this device type.
        Common examples: cpu, ram, storage, ports, capacity, size, type, speed, etc.
        """
        
        # Filter parent device choices for components
        if 'parent_device' in self.fields:
            self.fields['parent_device'].queryset = Device.objects.filter(
                device_type='COMPLETE'
            ).order_by('device_id')
    
    def clean_specifications(self):
        """Validate JSON specifications field."""
        specifications = self.cleaned_data.get('specifications')
        
        if not specifications:
            return {}
        
        # If it's already a dict, return as is
        if isinstance(specifications, dict):
            return specifications
        
        # If it's a string, try to parse as JSON
        if isinstance(specifications, str):
            try:
                parsed = json.loads(specifications)
                if not isinstance(parsed, dict):
                    raise ValidationError("Specifications must be a JSON object (dictionary)")
                return parsed
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {str(e)}")
        
        return specifications
    
    def clean(self):
        """Additional form validation."""
        cleaned_data = super().clean()
        device_type = cleaned_data.get('device_type')
        parent_device = cleaned_data.get('parent_device')
        
        # Validate parent device relationship
        if parent_device and device_type == 'COMPLETE':
            raise ValidationError("Complete devices cannot have parent devices")
        
        if parent_device and parent_device.device_type != 'COMPLETE':
            raise ValidationError("Parent device must be a complete device")
        
        return cleaned_data


# Inline Admins
class WarrantyInline(admin.TabularInline):
    """Inline admin for warranties."""
    model = Warranty
    extra = 0
    fields = ('warranty_type', 'provider', 'start_date', 'end_date', 'warranty_number', 'is_active')
    readonly_fields = ('created_at',)


class QRCodeInline(admin.TabularInline):
    """Inline admin for QR codes."""
    model = QRCode
    extra = 0
    fields = ('qr_code_preview', 'qr_data', 'is_active', 'created_at')
    readonly_fields = ('qr_code_preview', 'qr_data', 'created_at')
    
    def qr_code_preview(self, obj):
        """Display QR code image preview."""
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="50" height="50" />',
                obj.qr_code.url
            )
        return "No QR Code"
    qr_code_preview.short_description = "QR Code"


class ComponentInline(admin.TabularInline):
    """Inline admin for device components."""
    model = Device
    fk_name = 'parent_device'
    extra = 0
    fields = ('device_id', 'subcategory', 'brand', 'model', 'status', 'condition')
    readonly_fields = ('device_id',)
    verbose_name = "Component"
    verbose_name_plural = "Components"


# Main Admin Classes
@admin.register(DeviceCategory)
class DeviceCategoryAdmin(admin.ModelAdmin):
    """Admin interface for Device Categories."""
    
    list_display = (
        'name',
        'code',
        'get_icon_display',
        'get_subcategories_count',
        'get_devices_count',
        'get_available_devices_count',
        'is_active',
        'sort_order'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    ordering = ('sort_order', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Display Settings', {
            'fields': ('icon_class', 'sort_order', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def get_icon_display(self, obj):
        """Display icon in admin list."""
        return format_html(
            '<i class="{}"></i> {}',
            obj.icon_class,
            obj.icon_class
        )
    get_icon_display.short_description = 'Icon'
    
    def get_subcategories_count(self, obj):
        """Display subcategories count."""
        count = obj.get_subcategories_count()
        return format_html(
            '<span style="color: #007cba; font-weight: bold;">{}</span>',
            count
        )
    get_subcategories_count.short_description = 'Subcategories'
    
    def get_devices_count(self, obj):
        """Display total devices count."""
        count = obj.get_devices_count()
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">{}</span>',
            count
        )
    get_devices_count.short_description = 'Total Devices'
    
    def get_available_devices_count(self, obj):
        """Display available devices count."""
        count = obj.get_available_devices_count()
        return format_html(
            '<span style="color: #17a2b8; font-weight: bold;">{}</span>',
            count
        )
    get_available_devices_count.short_description = 'Available'


@admin.register(DeviceSubcategory)
class DeviceSubcategoryAdmin(admin.ModelAdmin):
    """Admin interface for Device Subcategories."""
    
    list_display = (
        'name',
        'full_code',
        'category',
        'get_devices_count',
        'get_available_devices_count',
        'is_active',
        'sort_order'
    )
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'description', 'category__name')
    ordering = ('category', 'sort_order', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'code', 'description')
        }),
        ('Settings', {
            'fields': ('sort_order', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def get_devices_count(self, obj):
        """Display devices count."""
        count = obj.get_devices_count()
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">{}</span>',
            count
        )
    get_devices_count.short_description = 'Devices'
    
    def get_available_devices_count(self, obj):
        """Display available devices count."""
        count = obj.get_available_devices_count()
        return format_html(
            '<span style="color: #17a2b8; font-weight: bold;">{}</span>',
            count
        )
    get_available_devices_count.short_description = 'Available'


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """Admin interface for Devices with comprehensive management features."""
    
    form = DeviceAdminForm
    
    list_display = (
        'device_id',
        'get_device_info',
        'get_category_info',
        'get_device_type_badge',
        'get_status_badge',
        'get_condition_badge',
        'get_specifications_summary',
        'purchase_date',
        'vendor',
        'get_warranty_status'
    )
    
    list_filter = (
        'status',
        'condition',
        'device_type',
        'subcategory__category',
        'subcategory',
        'vendor',
        'is_active',
        'is_assignable',
        'requires_approval',
        'purchase_date',
        'created_at'
    )
    
    search_fields = (
        'device_id',
        'brand',
        'model',
        'serial_number',
        'asset_tag',
        'notes'
    )
    
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Device Identification', {
            'fields': ('device_id', 'subcategory', 'device_type', 'parent_device')
        }),
        ('Device Details', {
            'fields': ('brand', 'model', 'serial_number', 'asset_tag')
        }),
        ('Status Information', {
            'fields': ('status', 'condition', 'priority'),
            'classes': ('wide',)
        }),
        ('Financial Information', {
            'fields': ('purchase_date', 'purchase_price', 'vendor'),
            'classes': ('collapse',)
        }),
        ('Location & Assignment', {
            'fields': ('current_location',),
            'classes': ('collapse',)
        }),
        ('Specifications', {
            'fields': ('specifications',),
            'description': 'Enter device specifications in JSON format. You can add any fields relevant to this device type.'
        }),
        ('Additional Information', {
            'fields': ('notes', 'barcode'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active', 'is_assignable', 'requires_approval'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('device_id', 'created_at', 'updated_at')
    
    inlines = [ComponentInline, WarrantyInline, QRCodeInline]
    
    actions = ['mark_as_available', 'mark_as_maintenance', 'mark_as_retired', 'export_devices']
    
    def get_device_info(self, obj):
        """Display device brand and model with image placeholder."""
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '<div style="margin-right: 10px;">'
            '<i class="bi-laptop" style="font-size: 24px; color: #007cba;"></i>'
            '</div>'
            '<div>'
            '<strong>{} {}</strong><br>'
            '<small style="color: #666;">S/N: {}</small>'
            '</div>'
            '</div>',
            obj.brand,
            obj.model,
            obj.serial_number
        )
    get_device_info.short_description = 'Device Information'
    
    def get_category_info(self, obj):
        """Display category and subcategory information."""
        return format_html(
            '<div>'
            '<span style="color: #007cba; font-weight: bold;">{}</span><br>'
            '<small>{}</small>'
            '</div>',
            obj.subcategory.category.name,
            obj.subcategory.name
        )
    get_category_info.short_description = 'Category'
    
    def get_device_type_badge(self, obj):
        """Display device type as badge."""
        colors = {
            'COMPLETE': '#007cba',
            'COMPONENT': '#17a2b8',
            'ACCESSORY': '#6c757d'
        }
        color = colors.get(obj.device_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_device_type_display()
        )
    get_device_type_badge.short_description = 'Type'
    
    def get_status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'AVAILABLE': '#28a745',
            'ASSIGNED': '#007cba',
            'MAINTENANCE': '#ffc107',
            'RETIRED': '#6c757d',
            'LOST': '#dc3545',
            'DAMAGED': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def get_condition_badge(self, obj):
        """Display condition as colored badge."""
        colors = {
            'NEW': '#28a745',
            'EXCELLENT': '#28a745',
            'GOOD': '#17a2b8',
            'FAIR': '#ffc107',
            'POOR': '#fd7e14',
            'DAMAGED': '#dc3545'
        }
        color = colors.get(obj.condition, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_condition_display()
        )
    get_condition_badge.short_description = 'Condition'
    
    def get_specifications_summary(self, obj):
        """Display key specifications summary."""
        if not obj.specifications:
            return format_html('<em style="color: #999;">No specifications</em>')
        
        # Get first 3 key-value pairs for summary
        specs = list(obj.specifications.items())[:3]
        summary_items = []
        
        for key, value in specs:
            display_key = key.replace('_', ' ').title()
            summary_items.append(f"{display_key}: {value}")
        
        summary = "<br>".join(summary_items)
        if len(obj.specifications) > 3:
            summary += f"<br><em>+{len(obj.specifications) - 3} more...</em>"
        
        return format_html(
            '<div style="font-size: 11px; line-height: 1.3;">{}</div>',
            summary
        )
    get_specifications_summary.short_description = 'Key Specifications'
    
    def get_warranty_status(self, obj):
        """Display warranty status."""
        if obj.is_under_warranty:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Under Warranty</span>'
            )
        elif obj.warranty_expires_soon:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">⚠ Expires Soon</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545;">✗ No Warranty</span>'
            )
    get_warranty_status.short_description = 'Warranty'
    
    def save_model(self, request, obj, form, change):
        """Override save to set created_by field."""
        if not change:  # Only for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    # Custom Actions
    def mark_as_available(self, request, queryset):
        """Mark selected devices as available."""
        updated = queryset.update(status='AVAILABLE')
        self.message_user(request, f'{updated} device(s) marked as available.')
    mark_as_available.short_description = "Mark selected devices as available"
    
    def mark_as_maintenance(self, request, queryset):
        """Mark selected devices as in maintenance."""
        updated = queryset.update(status='MAINTENANCE')
        self.message_user(request, f'{updated} device(s) marked as in maintenance.')
    mark_as_maintenance.short_description = "Mark selected devices as in maintenance"
    
    def mark_as_retired(self, request, queryset):
        """Mark selected devices as retired."""
        updated = queryset.update(status='RETIRED', is_assignable=False)
        self.message_user(request, f'{updated} device(s) marked as retired.')
    mark_as_retired.short_description = "Mark selected devices as retired"


@admin.register(Warranty)
class WarrantyAdmin(admin.ModelAdmin):
    """Admin interface for Warranties."""
    
    list_display = (
        'device',
        'warranty_type',
        'provider',
        'start_date',
        'end_date',
        'get_status_display',
        'get_days_remaining_display'
    )
    
    list_filter = (
        'warranty_type',
        'provider',
        'is_active',
        'start_date',
        'end_date'
    )
    
    search_fields = (
        'device__device_id',
        'device__brand',
        'device__model',
        'warranty_number',
        'provider__name'
    )
    
    ordering = ('-end_date',)
    
    fieldsets = (
        ('Warranty Information', {
            'fields': ('device', 'warranty_type', 'provider', 'warranty_number')
        }),
        ('Coverage Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Coverage Details', {
            'fields': ('coverage_description', 'terms_conditions')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'contact_phone', 'contact_email'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_status_display(self, obj):
        """Display warranty status with color coding."""
        if obj.is_expired:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Expired</span>'
            )
        elif obj.expires_soon:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">Expires Soon</span>'
            )
        else:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">Active</span>'
            )
    get_status_display.short_description = 'Status'
    
    def get_days_remaining_display(self, obj):
        """Display days remaining with color coding."""
        days = obj.days_remaining
        if days <= 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Expired</span>'
            )
        elif days <= 30:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">{} days</span>',
                days
            )
        else:
            return format_html(
                '<span style="color: #28a745;">{} days</span>',
                days
            )
    get_days_remaining_display.short_description = 'Days Remaining'


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    """Admin interface for QR Codes."""
    
    list_display = (
        'device',
        'get_qr_preview',
        'qr_code_id',
        'is_active',
        'created_at'
    )
    
    list_filter = ('is_active', 'format', 'created_at')
    
    search_fields = (
        'device__device_id',
        'device__brand',
        'device__model',
        'qr_data'
    )
    
    ordering = ('-created_at',)
    
    readonly_fields = ('qr_code_id', 'qr_data', 'created_at', 'updated_at')
    
    fieldsets = (
        ('QR Code Information', {
            'fields': ('device', 'qr_code_id', 'qr_code', 'qr_data')
        }),
        ('Settings', {
            'fields': ('size', 'format', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_qr_preview(self, obj):
        """Display QR code preview."""
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="80" height="80" style="border: 1px solid #ddd;" />',
                obj.qr_code.url
            )
        return "No QR Code"
    get_qr_preview.short_description = 'QR Code'


# Customize Admin Site
admin.site.site_header = 'PIMS Device Management'
admin.site.site_title = 'PIMS Devices Admin'
admin.site.index_title = 'Bangladesh Parliament Secretariat - Device Inventory Management'