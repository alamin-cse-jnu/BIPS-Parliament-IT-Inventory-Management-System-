"""
Models for Assignments app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines models for device assignment tracking including:
- Assignment model for tracking device assignments to users and locations
- Assignment history and lifecycle management
- Integration with devices, users, and locations apps
- Business logic for assignment validation and status tracking

Key Features:
- Device-to-user assignment tracking
- Optional location specification for assigned devices
- Assignment date and expected return date management
- Assignment status tracking (ASSIGNED, RETURNED, OVERDUE)
- Notes and reason tracking for assignments
- Auto-generated assignment IDs
- Assignment history and audit trails
- Validation rules for assignment eligibility
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
import uuid
from datetime import date, timedelta
import uuid
import os
from django.urls import reverse


class Assignment(models.Model):
    """
    Model for tracking device assignments to users and locations.
    
    This model manages the assignment of devices to users, tracking when
    devices are assigned, to whom, where they are located, and when they
    should be returned. It integrates with the devices, users, and locations
    apps to provide comprehensive asset tracking.
    
    Business Rules:
    - Only AVAILABLE devices can be assigned
    - Each device can have only one active assignment
    - Assignment automatically updates device status to ASSIGNED
    - Overdue assignments are tracked for follow-up
    - Assignment history is maintained for audit purposes
    """
    
    # Assignment Status Choices
    STATUS_CHOICES = [
        ('ASSIGNED', 'Assigned'),
        ('RETURNED', 'Returned'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Assignment Type Choices
    ASSIGNMENT_TYPE_CHOICES = [
        ('PERMANENT', 'Permanent Assignment'),
        ('TEMPORARY', 'Temporary Assignment'),
        ('MAINTENANCE', 'Maintenance Assignment'),
        ('PROJECT', 'Project Assignment'),
    ]
    
    # Primary Key and Identification
    id = models.AutoField(primary_key=True)
    assignment_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Auto-generated assignment ID (ASN-YYYY-NNNN)"
    )
    
    # Core Relationships
    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="Device being assigned"
    )
    assigned_to = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='device_assignments',
        help_text="User receiving the device assignment"
    )
    assigned_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments_made',
        help_text="User who made the assignment"
    )
    
    # Optional Location Assignment
    assigned_location = models.ForeignKey(
        'locations.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_assignments',
        help_text="Location where device will be used"
    )
    
    # Assignment Details
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPE_CHOICES,
        default='PERMANENT',
        help_text="Type of assignment"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ASSIGNED',
        help_text="Current assignment status"
    )
    
    # Date Management
    assigned_date = models.DateField(
        default=timezone.now,
        help_text="Date when device was assigned"
    )
    expected_return_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected return date (for temporary assignments)"
    )
    actual_return_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual date when device was returned"
    )
    
    # Assignment Purpose and Notes
    purpose = models.CharField(
        max_length=200,
        help_text="Purpose or reason for assignment"
    )
    assignment_notes = models.TextField(
        blank=True,
        help_text="Additional notes about this assignment"
    )
    return_notes = models.TextField(
        blank=True,
        help_text="Notes when device is returned"
    )
    
    # Condition Tracking
    condition_at_assignment = models.CharField(
        max_length=20,
        choices=[
            ('EXCELLENT', 'Excellent'),
            ('GOOD', 'Good'),
            ('FAIR', 'Fair'),
            ('POOR', 'Poor'),
        ],
        default='GOOD',
        help_text="Device condition when assigned"
    )
    condition_at_return = models.CharField(
        max_length=20,
        choices=[
            ('EXCELLENT', 'Excellent'),
            ('GOOD', 'Good'),
            ('FAIR', 'Fair'),
            ('POOR', 'Poor'),
            ('DAMAGED', 'Damaged'),
        ],
        blank=True,
        help_text="Device condition when returned"
    )
    
    # Contact and Emergency Information
    emergency_contact = models.CharField(
        max_length=100,
        blank=True,
        help_text="Emergency contact person"
    )
    emergency_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Emergency contact phone number"
    )
    
    # System Flags
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this assignment is currently active"
    )
    is_overdue = models.BooleanField(
        default=False,
        help_text="Whether this assignment is overdue"
    )
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignments_assignment'
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'
        ordering = ['-assigned_date', '-created_at']
        indexes = [
            models.Index(fields=['assignment_id']),
            models.Index(fields=['device', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['assigned_date', 'status']),
            models.Index(fields=['expected_return_date', 'status']),
            models.Index(fields=['is_active', 'status']),
        ]
        constraints = [
            # Ensure only one active assignment per device
            models.UniqueConstraint(
                fields=['device'],
                condition=models.Q(status='ASSIGNED', is_active=True),
                name='unique_active_device_assignment'
            ),
        ]
    
    def __str__(self):
        return f"{self.assignment_id}: {self.device.device_id} → {self.assigned_to.get_full_name()}"
    
    def save(self, *args, **kwargs):
        """Override save to generate assignment ID and handle business logic."""
        # Generate assignment ID if not exists
        if not self.assignment_id:
            self.assignment_id = self.generate_assignment_id()
        
        # Update overdue status
        self.update_overdue_status()
        
        # Call parent save
        super().save(*args, **kwargs)
        
        # Update device status based on assignment
        self.update_device_status()
    
    def clean(self):
        """Validate assignment data."""
        errors = {}
        
        # Check if device is available for assignment
        if self.device and self.status == 'ASSIGNED':
            if self.device.status != 'AVAILABLE':
                errors['device'] = f"Device {self.device.device_id} is not available for assignment (current status: {self.device.get_status_display()})"
            
            # Check for existing active assignments
            if not self.pk:  # New assignment
                existing = Assignment.objects.filter(
                    device=self.device,
                    status='ASSIGNED',
                    is_active=True
                ).exists()
                if existing:
                    errors['device'] = f"Device {self.device.device_id} already has an active assignment"
        
        # Validate dates
        if self.assigned_date and self.expected_return_date:
            if self.expected_return_date <= self.assigned_date:
                errors['expected_return_date'] = "Expected return date must be after assignment date"
        
        if self.assigned_date and self.actual_return_date:
            if self.actual_return_date < self.assigned_date:
                errors['actual_return_date'] = "Actual return date cannot be before assignment date"
        
        # Validate return conditions
        if self.status == 'RETURNED' and not self.actual_return_date:
            errors['actual_return_date'] = "Actual return date is required for returned assignments"
        
        if self.condition_at_return and not self.actual_return_date:
            errors['condition_at_return'] = "Return condition can only be set when device is returned"
        
        if errors:
            raise ValidationError(errors)
    
    @classmethod
    def generate_assignment_id(cls):
        """Generate unique assignment ID in format ASN-YYYY-NNNN."""
        current_year = timezone.now().year
        year_suffix = str(current_year)
        
        # Find the highest sequence number for current year
        last_assignment = cls.objects.filter(
            assignment_id__startswith=f'ASN-{year_suffix}-'
        ).order_by('-assignment_id').first()
        
        if last_assignment:
            try:
                last_sequence = int(last_assignment.assignment_id.split('-')[-1])
                new_sequence = last_sequence + 1
            except (ValueError, IndexError):
                new_sequence = 1
        else:
            new_sequence = 1
        
        return f'ASN-{year_suffix}-{new_sequence:04d}'
    
    def update_overdue_status(self):
        """Update overdue status based on expected return date."""
        if (self.status == 'ASSIGNED' and 
            self.expected_return_date and 
            self.expected_return_date < timezone.now().date()):
            self.is_overdue = True
            # Auto-update status to overdue if past expected return date
            if self.status == 'ASSIGNED':
                self.status = 'OVERDUE'
        else:
            self.is_overdue = False
    
    def update_device_status(self):
        """Update related device status based on assignment status."""
        if not self.device:
            return
        
        # Import here to avoid circular imports
        from devices.models import Device
        
        if self.status == 'ASSIGNED' and self.is_active:
            # Device should be marked as assigned
            if self.device.status != 'ASSIGNED':
                Device.objects.filter(id=self.device.id).update(status='ASSIGNED')
        
        elif self.status in ['RETURNED', 'CANCELLED'] or not self.is_active:
            # Check if device has other active assignments
            other_active = Assignment.objects.filter(
                device=self.device,
                status='ASSIGNED',
                is_active=True
            ).exclude(id=self.id).exists()
            
            if not other_active:
                # No other active assignments, mark device as available
                Device.objects.filter(id=self.device.id).update(status='AVAILABLE')
    
    def mark_returned(self, return_date=None, condition=None, notes='', returned_by=None):
        """Mark assignment as returned."""
        self.status = 'RETURNED'
        self.actual_return_date = return_date or timezone.now().date()
        self.is_active = False
        
        if condition:
            self.condition_at_return = condition
        
        if notes:
            self.return_notes = notes
        
        self.save()
        return True
    
    def cancel_assignment(self, reason='', cancelled_by=None):
        """Cancel assignment."""
        self.status = 'CANCELLED'
        self.is_active = False
        
        if reason:
            self.return_notes = f"Cancelled: {reason}"
        
        self.save()
        return True
    
    def extend_assignment(self, new_return_date, reason=''):
        """Extend assignment return date."""
        if self.status != 'ASSIGNED':
            raise ValidationError("Can only extend active assignments")
        
        self.expected_return_date = new_return_date
        self.update_overdue_status()
        
        if reason:
            current_notes = self.assignment_notes or ''
            self.assignment_notes = f"{current_notes}\nExtended to {new_return_date}: {reason}".strip()
        
        self.save()
        return True
    
    def days_assigned(self):
        """Calculate number of days device has been assigned."""
        if self.actual_return_date:
            return (self.actual_return_date - self.assigned_date).days
        return (timezone.now().date() - self.assigned_date).days

    def days_overdue(self):
        """Calculate number of days assignment is overdue."""
        if not self.expected_return_date or self.status != 'OVERDUE':
            return 0
        return (timezone.now().date() - self.expected_return_date).days
    
    def get_export_data(self):
        """Get assignment data formatted for export."""
        return {
            'assignment_id': self.assignment_id,
            'device_id': self.device.device_id if self.device else '',
            'device_name': self.device.name if self.device else '',
            'device_brand': self.device.brand if self.device else '',
            'device_model': self.device.model if self.device else '',
            'employee_name': self.assigned_to.get_full_name() if self.assigned_to else '',
            'employee_id': getattr(self.assigned_to, 'employee_id', '') if self.assigned_to else '',
            'location_name': self.assigned_location.name if self.assigned_location else '',
            'assignment_type': self.get_assignment_type_display(),
            'status': self.get_status_display(),
            'assigned_date': self.assigned_date,
            'expected_return_date': self.expected_return_date,
            'actual_return_date': self.actual_return_date,
            'purpose': self.purpose,
            'days_assigned': self.days_assigned(),
            'condition_at_assignment': self.get_condition_at_assignment_display(),
            'condition_at_return': self.get_condition_at_return_display() if self.condition_at_return else '',
            'assigned_by': self.assigned_by.get_full_name() if self.assigned_by else ''
        }
    
    @classmethod
    def get_export_queryset(cls, filters=None):
        """Get optimized queryset for exports."""
        queryset = cls.objects.select_related(
            'device', 'assigned_to', 'assigned_location', 'assigned_by'
        ).order_by('-assigned_date')
        
        if filters:
            # Apply filters
            if 'status' in filters and filters['status']:
                queryset = queryset.filter(status__in=filters['status'])
            if 'assignment_type' in filters and filters['assignment_type']:
                queryset = queryset.filter(assignment_type__in=filters['assignment_type'])
            if 'date_from' in filters and filters['date_from']:
                queryset = queryset.filter(assigned_date__gte=filters['date_from'])
            if 'date_to' in filters and filters['date_to']:
                queryset = queryset.filter(assigned_date__lte=filters['date_to'])
            if 'employee' in filters and filters['employee']:
                queryset = queryset.filter(assigned_to_id=filters['employee'])
            if 'location' in filters and filters['location']:
                queryset = queryset.filter(assigned_location_id=filters['location'])
        
        return queryset
    
    @classmethod
    def get_export_statistics(cls):
        """Get statistics for export summaries."""
        from django.db.models import Count, Q
        
        return {
            'total': cls.objects.count(),
            'active': cls.objects.filter(status='ACTIVE').count(),
            'returned': cls.objects.filter(status='RETURNED').count(),
            'overdue': cls.objects.filter(
                status='ACTIVE',
                expected_return_date__lt=timezone.now().date()
            ).count(),
            'temporary': cls.objects.filter(assignment_type='TEMPORARY').count(),
            'permanent': cls.objects.filter(assignment_type='PERMANENT').count(),
            'this_month': cls.objects.filter(
                assigned_date__month=timezone.now().month,
                assigned_date__year=timezone.now().year
            ).count(),
            'by_status': cls.objects.values('status').annotate(count=Count('id')),
            'by_type': cls.objects.values('assignment_type').annotate(count=Count('id')),
            'top_devices': cls.objects.values('device__name', 'device__device_id')
                .annotate(count=Count('id'))
                .order_by('-count')[:10],
            'top_employees': cls.objects.values('assigned_to__first_name', 'assigned_to__last_name')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
        }


    def get_absolute_url(self):
        """Return URL for assignment detail view."""
        return reverse('assignments:detail', kwargs={'pk': self.pk})
    
    @property
    def is_temporary(self):
        """Check if assignment is temporary."""
        return self.assignment_type == 'TEMPORARY' or bool(self.expected_return_date)
    
    @property
    def current_location_display(self):
        """Get display name for current location."""
        if self.assigned_location:
            return self.assigned_location.name
        elif self.assigned_to and hasattr(self.assigned_to, 'current_location'):
            return self.assigned_to.current_location.name if self.assigned_to.current_location else 'Not specified'
        return 'Not specified'
    
    @classmethod
    def get_overdue_assignments(cls):
        """Get all overdue assignments."""
        return cls.objects.filter(
            status='ASSIGNED',
            is_active=True,
            expected_return_date__lt=timezone.now().date()
        )
    
    @classmethod
    def get_assignments_due_soon(cls, days=7):
        """Get assignments due within specified days."""
        due_date = timezone.now().date() + timedelta(days=days)
        return cls.objects.filter(
            status='ASSIGNED',
            is_active=True,
            expected_return_date__lte=due_date,
            expected_return_date__gte=timezone.now().date()
        )

class AssignmentQRCode(models.Model):
    """
    QR codes for assignment identification and tracking.
    Generated automatically when assignments are created or updated.
    Follows the same pattern as Device QRCode model for consistency.
    """
    
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='qr_codes',
        help_text="Assignment this QR code represents"
    )
    
    # QR Code Details
    qr_code_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text="Unique QR code identifier"
    )
    qr_code = models.ImageField(
        upload_to='qrcodes/assignments/',
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
        db_table = 'assignments_assignmentqrcode'
        verbose_name = 'Assignment QR Code'
        verbose_name_plural = 'Assignment QR Codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assignment', 'is_active']),
            models.Index(fields=['qr_code_id']),
        ]
    
    def __str__(self):
        return f"QR Code for {self.assignment.assignment_id}"
    
    def save(self, *args, **kwargs):
        # Deactivate other QR codes for this assignment
        if self.is_active:
            AssignmentQRCode.objects.filter(assignment=self.assignment, is_active=True).exclude(
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
        return reverse('assignments:qr_download', kwargs={'pk': self.pk})
    
    @property
    def file_exists(self):
        """Check if QR code file exists."""
        return self.qr_code and os.path.isfile(self.qr_code.path)