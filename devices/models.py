"""
Models for Devices app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines models for device management including:
- DeviceCategory: Main categories (Computers, Storage, Network, Components, etc.)
- DeviceSubcategory: Subcategories under main categories
- Device: Individual devices with flexible JSON specifications
- Warranty: Warranty information for devices
- QRCode: QR codes for device identification

Features:
- Complete devices (Laptop, Desktop) vs Components (RAM, CPU, Storage)
- Flexible JSON specifications - admin can add any field needed
- Simple category structure for Bangladesh Parliament Secretariat
"""

import os
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta


class DeviceCategory(models.Model):
    """
    Main device categories for Parliament IT inventory.
    Examples: Computers, Storage, Network, Components, Accessories, Power
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., Computers, Storage, Network Equipment)"
    )
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short code for category (e.g., COMP, STOR, NET)"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of this device category"
    )
    icon_class = models.CharField(
        max_length=50,
        default='bi-laptop',
        help_text="Bootstrap icon class for UI display"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this category is actively used"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices_category'
        verbose_name = 'Device Category'
        verbose_name_plural = 'Device Categories'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        """Validate model data."""
        if self.code:
            self.code = self.code.upper().strip()
        if self.name:
            self.name = self.name.strip()
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_subcategories_count(self):
        """Return count of active subcategories in this category."""
        return self.subcategories.filter(is_active=True).count()
    
    def get_devices_count(self):
        """Return total count of devices in this category."""
        return Device.objects.filter(subcategory__category=self).count()
    
    def get_available_devices_count(self):
        """Return count of available devices in this category."""
        return Device.objects.filter(
            subcategory__category=self,
            status='AVAILABLE'
        ).count()


class DeviceSubcategory(models.Model):
    """
    Subcategories under main device categories.
    Examples: Laptop/Desktop under Computers, RAM/CPU under Components
    """
    
    category = models.ForeignKey(
        DeviceCategory,
        on_delete=models.CASCADE,
        related_name='subcategories',
        help_text="Parent category"
    )
    name = models.CharField(
        max_length=100,
        help_text="Subcategory name (e.g., Laptops, Desktop Computers, RAM)"
    )
    code = models.CharField(
        max_length=15,
        help_text="Short code (e.g., LAP, DESK, RAM)"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of this subcategory"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this subcategory is actively used"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within category"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices_subcategory'
        verbose_name = 'Device Subcategory'
        verbose_name_plural = 'Device Subcategories'
        ordering = ['category', 'sort_order', 'name']
        unique_together = ['category', 'code']
    
    def __str__(self):
        return f"{self.category.code}-{self.code}: {self.name}"
    
    def clean(self):
        """Validate model data."""
        if self.code:
            self.code = self.code.upper().strip()
        if self.name:
            self.name = self.name.strip()
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def full_code(self):
        """Return complete code including category."""
        return f"{self.category.code}-{self.code}"
    
    def get_devices_count(self):
        """Return count of devices in this subcategory."""
        return self.devices.count()
    
    def get_available_devices_count(self):
        """Return count of available devices in this subcategory."""
        return self.devices.filter(status='AVAILABLE').count()


class Device(models.Model):
    """
    Individual devices in the Parliament IT inventory.
    Supports both complete devices (Laptop, Desktop) and components (RAM, CPU, Storage).
    Uses flexible JSON specifications for different device types.
    """
    
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('ASSIGNED', 'Assigned'),
        ('MAINTENANCE', 'In Maintenance'),
        ('RETIRED', 'Retired'),
        ('LOST', 'Lost/Missing'),
        ('DAMAGED', 'Damaged'),
    ]
    
    CONDITION_CHOICES = [
        ('NEW', 'New'),
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('POOR', 'Poor'),
        ('DAMAGED', 'Damaged'),
    ]
    
    DEVICE_TYPES = [
        ('COMPLETE', 'Complete Device'),      # Desktop, Laptop, Printer, Router
        ('COMPONENT', 'Component'),           # RAM, CPU, Storage, Monitor
        ('ACCESSORY', 'Accessory'),           # Mouse, Keyboard, Cables
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Basic Information
    device_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique device identifier (auto-generated if empty)"
    )
    subcategory = models.ForeignKey(
        DeviceSubcategory,
        on_delete=models.CASCADE,
        related_name='devices',
        help_text="Device subcategory"
    )
    
    # Device Type and Hierarchy
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPES,
        default='COMPLETE',
        help_text="Type of device - Complete device, Component, or Accessory"
    )
    parent_device = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='components',
        help_text="Parent device if this is a component (e.g., RAM belongs to Desktop)"
    )
    
    # Device Details
    brand = models.CharField(
        max_length=100,
        help_text="Device brand/manufacturer (e.g., Dell, HP, Cisco, Intel)"
    )
    model = models.CharField(
        max_length=150,
        help_text="Device model number/name"
    )
    serial_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Manufacturer serial number"
    )
    asset_tag = models.CharField(
        max_length=50,
        blank=True,
        help_text="Internal asset tag number"
    )
    
    # Status and Condition
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='AVAILABLE',
        help_text="Current device status"
    )
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='NEW',
        help_text="Physical condition of device"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='MEDIUM',
        help_text="Device priority level"
    )
    
    # Financial Information
    purchase_date = models.DateField(
        help_text="Date when device was purchased"
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Purchase price in BDT"
    )
    vendor = models.ForeignKey(
        'vendors.Vendor',
        on_delete=models.PROTECT,
        related_name='devices',
        help_text="Vendor who supplied this device"
    )
    
    # Location Information
    current_location = models.ForeignKey(
        'locations.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices',
        help_text="Current physical location"
    )
    
    # Flexible Specifications (JSON) - Admin can add any field they need
    specifications = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Device specifications in JSON format. Examples:
        Desktop/Laptop: {"cpu": "Intel i5-12400", "ram": "16GB DDR4", "storage": "512GB SSD", "monitor": "24 inch Dell"}
        Pendrive: {"capacity": "64GB", "type": "USB 3.0", "interface": "USB-A"}
        Router: {"model": "Cisco ISR 4000", "ports": "24 Port Gigabit", "wifi": "802.11ac"}
        RAM: {"size": "8GB", "type": "DDR4", "speed": "3200MHz", "form_factor": "DIMM"}
        """
    )
    
    # Additional Information
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this device"
    )
    barcode = models.CharField(
        max_length=100,
        blank=True,
        help_text="Internal barcode if different from device_id"
    )
    

    
    # Flags
    is_active = models.BooleanField(
        default=True,
        help_text="Whether device is active in inventory"
    )
    is_assignable = models.BooleanField(
        default=True,
        help_text="Whether device can be assigned to users"
    )
    requires_approval = models.BooleanField(
        default=False,
        help_text="Whether assignment requires special approval"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_devices',
        help_text="User who created this device record"
    )
    
    class Meta:
        db_table = 'devices_device'
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['serial_number']),
            models.Index(fields=['status']),
            models.Index(fields=['device_type']),
            models.Index(fields=['subcategory', 'status']),
        ]
    
    def __str__(self):
        if self.device_type == 'COMPONENT' and self.parent_device:
            return f"{self.device_id}: {self.brand} {self.model} (Component of {self.parent_device.device_id})"
        return f"{self.device_id}: {self.brand} {self.model}"
    
    def clean(self):
        """Validate model data."""
        errors = {}
        
        # Validate device_id format
        if self.device_id:
            self.device_id = self.device_id.upper().strip()
        
        # Validate serial number
        if self.serial_number:
            self.serial_number = self.serial_number.strip()
        
        # Validate parent device relationship
        if self.parent_device:
            if self.parent_device == self:
                errors['parent_device'] = "Device cannot be its own parent"
            
            if self.device_type == 'COMPLETE':
                errors['device_type'] = "Complete devices cannot have parent devices"
            
            if self.parent_device.device_type != 'COMPLETE':
                errors['parent_device'] = "Parent device must be a complete device"
        
        # Component validation
        if self.device_type == 'COMPONENT':
            if not self.parent_device:
                # Components can exist without parent (spare parts)
                pass
        
        # Validate status transitions
        if self.pk:  # Only for existing devices
            try:
                old_device = Device.objects.get(pk=self.pk)
                if old_device.status != self.status:
                    if not self._is_valid_status_transition(old_device.status, self.status):
                        errors['status'] = f"Invalid status transition from {old_device.status} to {self.status}"
            except Device.DoesNotExist:
                pass
        
        # Business rules validation
        if self.status == 'ASSIGNED' and not self.is_assignable:
            errors['status'] = "Device marked as non-assignable cannot be assigned"
        
        if self.condition == 'DAMAGED' and self.status == 'AVAILABLE':
            errors['status'] = "Damaged devices should not be available for assignment"
        
        # Date validations
        if self.purchase_date and self.purchase_date > date.today():
            errors['purchase_date'] = "Purchase date cannot be in the future"
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save method for additional processing."""
        # Auto-generate device_id if not provided
        if not self.device_id:
            self.device_id = self._generate_device_id()
        
        # Normalize data
        if self.brand:
            self.brand = self.brand.strip()
        if self.model:
            self.model = self.model.strip()
        
        # Set flags based on status
        if self.status in ['RETIRED', 'LOST', 'DAMAGED']:
            self.is_assignable = False
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def _generate_device_id(self):
        """Generate unique device ID."""
        prefix = f"{self.subcategory.category.code}{self.subcategory.code}"
        year = timezone.now().year % 100  # Last 2 digits of year
        
        # Find the next sequential number
        existing_devices = Device.objects.filter(
            device_id__startswith=f"{prefix}{year:02d}"
        ).count()
        
        sequence = existing_devices + 1
        return f"{prefix}{year:02d}{sequence:04d}"
    
    def generate_device_id(self):
        """
        Public method to generate device ID (for form compatibility).
        This is the method that forms can call.
        """
        return self._generate_device_id()
    
    def _is_valid_status_transition(self, old_status, new_status):
        """Check if status transition is valid."""
        valid_transitions = {
            'AVAILABLE': ['ASSIGNED', 'MAINTENANCE', 'RETIRED', 'LOST', 'DAMAGED'],
            'ASSIGNED': ['AVAILABLE', 'MAINTENANCE', 'RETIRED', 'LOST', 'DAMAGED'],
            'MAINTENANCE': ['AVAILABLE', 'RETIRED', 'DAMAGED'],
            'RETIRED': [],  # Terminal state
            'LOST': ['AVAILABLE'],  # If found
            'DAMAGED': ['MAINTENANCE', 'RETIRED'],
        }
        return new_status in valid_transitions.get(old_status, [])
    
    @property
    def full_name(self):
        """Return full device name for display."""
        return f"{self.brand} {self.model} ({self.device_id})"
    
    @property
    def category(self):
        """Return device category."""
        return self.subcategory.category
    
    @property
    def age_in_years(self):
        """Calculate device age in years."""
        return (date.today() - self.purchase_date).days / 365.25
    
    @property
    def is_under_warranty(self):
        """Check if device is under warranty."""
        return self.warranties.filter(
            start_date__lte=date.today(),
            end_date__gte=date.today(),
            is_active=True
        ).exists()
    
    @property
    def warranty_expires_soon(self):
        """Check if warranty expires within 30 days."""
        thirty_days_later = date.today() + timedelta(days=30)
        return self.warranties.filter(
            end_date__range=[date.today(), thirty_days_later],
            is_active=True
        ).exists()
    
    def get_absolute_url(self):
        """Return absolute URL for device detail view."""
        return reverse('devices:detail', kwargs={'pk': self.pk})
    
    def get_qr_code_url(self):
        """Return URL for device QR code."""
        try:
            qr_code = self.qr_codes.filter(is_active=True).first()
            return qr_code.qr_code.url if qr_code and qr_code.qr_code else None
        except:
            return None
    
    def get_current_assignment(self):
        """Get current active assignment."""
        try:
            from assignments.models import Assignment
            return Assignment.objects.filter(
                device=self,
                is_active=True
            ).first()
        except ImportError:
            return None
    
    def get_maintenance_history(self):
        """Get maintenance history for this device."""
        try:
            from maintenance.models import Maintenance
            return Maintenance.objects.filter(device=self).order_by('-start_date')
        except ImportError:
            return []
    
    def get_components(self):
        """Get all components belonging to this device."""
        return self.components.filter(is_active=True).order_by('subcategory__name')
    
    def get_specifications_display(self):
        """Return formatted specifications for display."""
        if not self.specifications:
            return "No specifications available"
        
        specs = []
        for key, value in self.specifications.items():
            # Format key for display
            display_key = key.replace('_', ' ').title()
            specs.append(f"{display_key}: {value}")
        
        return " | ".join(specs)
    
    def can_be_assigned(self):
        """Check if device can be assigned."""
        return (
            self.is_active and
            self.is_assignable and
            self.status == 'AVAILABLE' and
            self.condition not in ['DAMAGED', 'POOR']
        )
    
    def can_have_components(self):
        """Check if device can have components."""
        return self.device_type == 'COMPLETE'
    
    def get_status_badge_class(self):
        """Return CSS class for status badge."""
        status_classes = {
            'AVAILABLE': 'badge bg-success',
            'ASSIGNED': 'badge bg-primary',
            'MAINTENANCE': 'badge bg-warning',
            'RETIRED': 'badge bg-secondary',
            'LOST': 'badge bg-danger',
            'DAMAGED': 'badge bg-danger',
        }
        return status_classes.get(self.status, 'badge bg-secondary')
    
    def get_condition_badge_class(self):
        """Return CSS class for condition badge."""
        condition_classes = {
            'NEW': 'badge bg-success',
            'EXCELLENT': 'badge bg-success',
            'GOOD': 'badge bg-info',
            'FAIR': 'badge bg-warning',
            'POOR': 'badge bg-warning',
            'DAMAGED': 'badge bg-danger',
        }
        return condition_classes.get(self.condition, 'badge bg-secondary')
    
    def get_device_type_badge_class(self):
        """Return CSS class for device type badge."""
        type_classes = {
            'COMPLETE': 'badge bg-primary',
            'COMPONENT': 'badge bg-info',
            'ACCESSORY': 'badge bg-secondary',
        }
        return type_classes.get(self.device_type, 'badge bg-secondary')


class Warranty(models.Model):
    """
    Warranty information for devices.
    Supports multiple warranties per device (different components/services).
    """
    
    WARRANTY_TYPES = [
        ('MANUFACTURER', 'Manufacturer Warranty'),
        ('EXTENDED', 'Extended Warranty'),
        ('MAINTENANCE', 'Maintenance Contract'),
        ('SUPPORT', 'Support Contract'),
        ('INSURANCE', 'Insurance Coverage'),
    ]
    
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='warranties',
        help_text="Device covered by this warranty"
    )
    warranty_type = models.CharField(
        max_length=20,
        choices=WARRANTY_TYPES,
        default='MANUFACTURER',
        help_text="Type of warranty coverage"
    )
    provider = models.ForeignKey(
        'vendors.Vendor',
        on_delete=models.CASCADE,
        related_name='warranties',
        help_text="Warranty provider"
    )
    
    # Warranty Details
    warranty_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Warranty reference number"
    )
    start_date = models.DateField(
        help_text="Warranty start date"
    )
    end_date = models.DateField(
        help_text="Warranty end date"
    )
    
    # Coverage Details
    coverage_description = models.TextField(
        help_text="Description of what is covered"
    )
    terms_conditions = models.TextField(
        blank=True,
        help_text="Terms and conditions"
    )
    
    # Contact Information
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        help_text="Contact person for warranty claims"
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number"
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="Contact email address"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether warranty is currently active"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices_warranty'
        verbose_name = 'Warranty'
        verbose_name_plural = 'Warranties'
        ordering = ['-end_date']
        unique_together = ['device', 'warranty_type', 'provider', 'start_date']
    
    def __str__(self):
        return f"{self.device.device_id} - {self.get_warranty_type_display()} ({self.provider.name})"
    
    def clean(self):
        """Validate warranty data."""
        errors = {}
        
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                errors['end_date'] = "End date must be after start date"
        
        if self.start_date and self.start_date > date.today() + timedelta(days=365):
            errors['start_date'] = "Start date seems too far in the future"
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if warranty has expired."""
        return date.today() > self.end_date
    
    @property
    def expires_soon(self):
        """Check if warranty expires within 30 days."""
        thirty_days_later = date.today() + timedelta(days=30)
        return self.end_date <= thirty_days_later and not self.is_expired
    
    @property
    def days_remaining(self):
        """Calculate days remaining until expiry."""
        if self.is_expired:
            return 0
        return (self.end_date - date.today()).days
    
    @property
    def coverage_duration(self):
        """Calculate total coverage duration in days."""
        return (self.end_date - self.start_date).days


class QRCode(models.Model):
    """
    QR codes for device identification and tracking.
    Generated automatically when devices are created or updated.
    """
    
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='qr_codes',
        help_text="Device this QR code represents"
    )
    
    # QR Code Details
    qr_code_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text="Unique QR code identifier"
    )
    qr_code = models.ImageField(
        upload_to='qrcodes/devices/',
        help_text="Generated QR code image"
    )
    qr_data = models.TextField(
        help_text="Data encoded in the QR code"
    )
    
    # Metadata
    size = models.PositiveIntegerField(
        default=200,
        help_text="QR code size in pixels"
    )
    format = models.CharField(
        max_length=10,
        default='PNG',
        help_text="Image format"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this QR code is currently active"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices_qrcode'
        verbose_name = 'QR Code'
        verbose_name_plural = 'QR Codes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"QR Code for {self.device.device_id}"
    
    def save(self, *args, **kwargs):
        # Deactivate other QR codes for this device
        if self.is_active:
            QRCode.objects.filter(device=self.device, is_active=True).exclude(
                pk=self.pk
            ).update(is_active=False)
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete QR code file when model is deleted."""
        if self.qr_code and os.path.isfile(self.qr_code.path):
            os.remove(self.qr_code.path)
        super().delete(*args, **kwargs)
    
    def get_download_url(self):
        """Return URL for downloading QR code."""
        return reverse('devices:qr_download', kwargs={'pk': self.pk})