"""
Maintenance Models for PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines the Maintenance model for tracking device maintenance,
repairs, and service activities with automated status management and
integration with the Device model.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
import uuid

User = get_user_model()


class MaintenanceManager(models.Manager):
    """Custom manager for Maintenance model."""
    
    def active(self):
        """Return active maintenance records."""
        return self.filter(is_active=True)
    
    def in_progress(self):
        """Return maintenance records currently in progress."""
        return self.filter(status='IN_PROGRESS', is_active=True)
    
    def completed(self):
        """Return completed maintenance records."""
        return self.filter(status='COMPLETED')
    
    def overdue(self):
        """Return overdue maintenance records."""
        today = timezone.now().date()
        return self.filter(
            expected_end_date__lt=today,
            status__in=['SCHEDULED', 'IN_PROGRESS'],
            is_active=True
        )
    
    def due_soon(self, days=7):
        """Return maintenance records due within specified days."""
        future_date = timezone.now().date() + timedelta(days=days)
        return self.filter(
            expected_end_date__lte=future_date,
            status='SCHEDULED',
            is_active=True
        )
    
    def by_device(self, device):
        """Return maintenance history for a specific device."""
        return self.filter(device=device).order_by('-start_date')
    
    def by_vendor(self, vendor):
        """Return maintenance records for a specific vendor."""
        return self.filter(vendor=vendor).order_by('-start_date')
    
    def this_month(self):
        """Return maintenance records for current month."""
        today = timezone.now().date()
        return self.filter(
            start_date__year=today.year,
            start_date__month=today.month
        )
    
    def cost_summary(self):
        """Return cost summary for maintenance."""
        return self.aggregate(
            total_cost=models.Sum('actual_cost'),
            avg_cost=models.Avg('actual_cost'),
            count=models.Count('id')
        )


class Maintenance(models.Model):
    """
    Model for tracking device maintenance, repairs, and service activities.
    
    Handles the complete maintenance lifecycle from scheduling to completion
    with automated device status management and cost tracking.
    """
    
    # Maintenance Types
    MAINTENANCE_TYPES = [
        ('PREVENTIVE', 'Preventive Maintenance'),
        ('CORRECTIVE', 'Corrective Maintenance'),
        ('EMERGENCY', 'Emergency Repair'),
        ('UPGRADE', 'Hardware Upgrade'),
        ('INSPECTION', 'Safety Inspection'),
        ('CLEANING', 'Deep Cleaning'),
        ('CALIBRATION', 'Calibration'),
        ('REPLACEMENT', 'Component Replacement'),
        ('WARRANTY', 'Warranty Service'),
        ('OTHER', 'Other Service'),
    ]
    
    # Priority Levels
    PRIORITY_CHOICES = [
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('CRITICAL', 'Critical - Immediate'),
        ('EMERGENCY', 'Emergency - Urgent'),
    ]
    
    # Maintenance Status
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed/Unsuccessful'),
    ]
    
    # Service Provider Types
    PROVIDER_TYPES = [
        ('INTERNAL', 'Internal IT Team'),
        ('VENDOR', 'External Vendor'),
        ('MANUFACTURER', 'Manufacturer Service'),
        ('THIRD_PARTY', 'Third Party Service'),
    ]
    
    # Maintenance Results
    RESULT_CHOICES = [
        ('SUCCESS', 'Successful - Device Fully Operational'),
        ('PARTIAL', 'Partial Success - Limited Functionality'),
        ('FAILED', 'Failed - Device Still Non-functional'),
        ('REPLACED', 'Component/Device Replaced'),
        ('UPGRADED', 'Successfully Upgraded'),
        ('PENDING', 'Pending Further Action'),
    ]
    
    # Core Identification
    maintenance_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Auto-generated maintenance ID (MNT-YYYY-NNNN)"
    )
    
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique identifier for tracking"
    )
    
    # Device Relationship
    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.PROTECT,
        related_name='maintenance_records',
        help_text="Device being maintained"
    )
    
    # Maintenance Details
    maintenance_type = models.CharField(
        max_length=20,
        choices=MAINTENANCE_TYPES,
        default='PREVENTIVE',
        help_text="Type of maintenance being performed"
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='MEDIUM',
        help_text="Priority level for this maintenance"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED',
        help_text="Current status of maintenance"
    )
    
    # Scheduling Information
    start_date = models.DateField(
        help_text="Scheduled start date for maintenance"
    )
    
    expected_end_date = models.DateField(
        help_text="Expected completion date"
    )
    
    actual_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual date/time when maintenance started"
    )
    
    actual_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual date/time when maintenance completed"
    )
    
    # Service Provider Information
    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_TYPES,
        default='INTERNAL',
        help_text="Type of service provider"
    )
    
    vendor = models.ForeignKey(
        'vendors.Vendor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_services',
        help_text="External vendor providing service (if applicable)"
    )
    
    technician_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of primary technician"
    )
    
    technician_contact = models.CharField(
        max_length=15,
        blank=True,
        help_text="Contact number for technician"
    )
    
    # Cost Information
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Estimated cost for maintenance (BDT)"
    )
    
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text="Actual cost incurred (BDT)"
    )
    
    parts_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Cost of replacement parts (BDT)"
    )
    
    labor_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Labor cost (BDT)"
    )
    
    # Descriptions and Notes
    title = models.CharField(
        max_length=200,
        help_text="Brief title describing the maintenance"
    )
    
    description = models.TextField(
        help_text="Detailed description of maintenance required"
    )
    
    problem_reported = models.TextField(
        blank=True,
        help_text="Description of reported problem/issue"
    )
    
    work_performed = models.TextField(
        blank=True,
        help_text="Detailed description of work performed"
    )
    
    parts_replaced = models.TextField(
        blank=True,
        help_text="List of parts/components replaced"
    )
    
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        blank=True,
        help_text="Result/outcome of maintenance"
    )
    
    result_notes = models.TextField(
        blank=True,
        help_text="Additional notes about maintenance result"
    )
    
    # Quality and Performance
    satisfaction_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Service satisfaction rating (1-5 stars)"
    )
    
    downtime_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text="Total downtime in hours"
    )
    
    # Follow-up Information
    follow_up_required = models.BooleanField(
        default=False,
        help_text="Whether follow-up maintenance is required"
    )
    
    follow_up_date = models.DateField(
        null=True,
        blank=True,
        help_text="Scheduled follow-up date"
    )
    
    next_maintenance_due = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled maintenance date"
    )
    
    # Approval and Authorization
    requires_approval = models.BooleanField(
        default=False,
        help_text="Whether this maintenance requires management approval"
    )
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_maintenance',
        help_text="User who approved this maintenance"
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date/time when maintenance was approved"
    )
    
    # System Fields
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this maintenance record is active"
    )
    
    is_warranty_service = models.BooleanField(
        default=False,
        help_text="Whether this is covered under warranty"
    )
    
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal notes for IT team (not visible to users)"
    )
    
    # Audit Fields
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_maintenance',
        help_text="User who created this maintenance record"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date/time when record was created"
    )
    
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_maintenance',
        help_text="User who last updated this record"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date/time when record was last updated"
    )
    
    # Custom Manager
    objects = MaintenanceManager()
    
    class Meta:
        db_table = 'pims_maintenance'
        verbose_name = 'Maintenance Record'
        verbose_name_plural = 'Maintenance Records'
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['device', 'status']),
            models.Index(fields=['start_date', 'expected_end_date']),
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['maintenance_type', 'priority']),
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ('view_maintenance_costs', 'Can view maintenance costs'),
            ('approve_maintenance', 'Can approve maintenance requests'),
            ('manage_emergency_maintenance', 'Can manage emergency maintenance'),
            ('view_internal_notes', 'Can view internal maintenance notes'),
        ]
    
    def __str__(self):
        return f"{self.maintenance_id or 'MNT-NEW'} - {self.device.device_id} ({self.get_maintenance_type_display()})"
    
    def __repr__(self):
        return f"<Maintenance: {self.maintenance_id} - {self.device.device_id} - {self.status}>"
    
    def save(self, *args, **kwargs):
        """Override save method for additional processing."""
        # Generate maintenance ID if not provided
        if not self.maintenance_id:
            self.maintenance_id = self._generate_maintenance_id()
        
        # Auto-calculate actual cost if parts and labor are provided
        if self.parts_cost and self.labor_cost and not self.actual_cost:
            self.actual_cost = self.parts_cost + self.labor_cost
        
        # Set actual start date when status changes to IN_PROGRESS
        if self.status == 'IN_PROGRESS' and not self.actual_start_date:
            self.actual_start_date = timezone.now()
        
        # Set actual end date when status changes to COMPLETED
        if self.status == 'COMPLETED' and not self.actual_end_date:
            self.actual_end_date = timezone.now()
        
        # Validation
        self.full_clean()
        
        # Save the record
        super().save(*args, **kwargs)
        
        # Update device status based on maintenance status
        self._update_device_status()
    
    def clean(self):
        """Validate model data."""
        errors = {}
        
        # Date validations
        if self.start_date and self.expected_end_date:
            if self.start_date >= self.expected_end_date:
                errors['expected_end_date'] = "End date must be after start date"
        
        if self.actual_start_date and self.actual_end_date:
            if self.actual_start_date >= self.actual_end_date:
                errors['actual_end_date'] = "Actual end date must be after actual start date"
        
        # Cost validations
        if self.actual_cost and self.estimated_cost:
            cost_difference = abs(self.actual_cost - self.estimated_cost)
            if cost_difference > (self.estimated_cost * Decimal('0.5')):  # 50% variance
                # This is a warning, not an error - just log it
                pass
        
        # Status validations
        if self.status == 'COMPLETED':
            if not self.work_performed:
                errors['work_performed'] = "Work performed description is required for completed maintenance"
            if not self.result:
                errors['result'] = "Maintenance result is required for completed maintenance"
        
        if self.status == 'IN_PROGRESS':
            if self.device.status != 'MAINTENANCE':
                # Device status will be updated automatically
                pass
        
        # Approval validations
        if self.requires_approval and self.status != 'SCHEDULED':
            if not self.approved_by or not self.approved_at:
                errors['requires_approval'] = "Maintenance requiring approval must be approved before proceeding"
        
        # Vendor validations
        if self.provider_type == 'VENDOR' and not self.vendor:
            errors['vendor'] = "Vendor must be specified when provider type is 'Vendor'"
        
        if errors:
            raise ValidationError(errors)
    
    def _generate_maintenance_id(self):
        """Generate unique maintenance ID."""
        year = timezone.now().year
        
        # Get the last maintenance ID for current year
        last_maintenance = Maintenance.objects.filter(
            maintenance_id__startswith=f'MNT-{year}-'
        ).order_by('-maintenance_id').first()
        
        if last_maintenance:
            try:
                last_number = int(last_maintenance.maintenance_id.split('-')[-1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1
        
        return f'MNT-{year}-{next_number:04d}'
    
    def _update_device_status(self):
        """Update device status based on maintenance status."""
        try:
            if self.status == 'IN_PROGRESS':
                # Set device to maintenance status
                if self.device.status != 'MAINTENANCE':
                    self.device.status = 'MAINTENANCE'
                    self.device.save(update_fields=['status'])
            
            elif self.status == 'COMPLETED':
                # Check if device has any other active maintenance
                other_active = Maintenance.objects.filter(
                    device=self.device,
                    status__in=['SCHEDULED', 'IN_PROGRESS'],
                    is_active=True
                ).exclude(id=self.id).exists()
                
                if not other_active:
                    # No other active maintenance, device can be available
                    self.device.status = 'AVAILABLE'
                    self.device.save(update_fields=['status'])
            
            elif self.status in ['CANCELLED', 'FAILED']:
                # Check if device has any other active maintenance
                other_active = Maintenance.objects.filter(
                    device=self.device,
                    status__in=['SCHEDULED', 'IN_PROGRESS'],
                    is_active=True
                ).exclude(id=self.id).exists()
                
                if not other_active:
                    # No other active maintenance
                    if self.status == 'FAILED' and self.result in ['FAILED', 'PENDING']:
                        # Device might be damaged
                        self.device.status = 'DAMAGED'
                    else:
                        self.device.status = 'AVAILABLE'
                    self.device.save(update_fields=['status'])
                    
        except Exception as e:
            # Log error but don't fail the save
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating device status for maintenance {self.id}: {e}")
    
    def get_absolute_url(self):
        """Return URL for this maintenance record."""
        return reverse('maintenance:detail', kwargs={'pk': self.pk})
    
    # Status Properties
    @property
    def is_overdue(self):
        """Check if maintenance is overdue."""
        if self.status in ['COMPLETED', 'CANCELLED']:
            return False
        return timezone.now().date() > self.expected_end_date
    
    @property
    def is_due_soon(self, days=7):
        """Check if maintenance is due within specified days."""
        if self.status != 'SCHEDULED':
            return False
        future_date = timezone.now().date() + timedelta(days=days)
        return self.start_date <= future_date
    
    @property
    def is_in_progress(self):
        """Check if maintenance is currently in progress."""
        return self.status == 'IN_PROGRESS'
    
    @property
    def is_completed(self):
        """Check if maintenance is completed."""
        return self.status == 'COMPLETED'
    
    @property
    def days_until_due(self):
        """Calculate days until maintenance is due."""
        if self.start_date <= timezone.now().date():
            return 0
        return (self.start_date - timezone.now().date()).days
    
    @property
    def days_overdue(self):
        """Calculate days overdue (if any)."""
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.expected_end_date).days
    
    # Duration Properties
    @property
    def planned_duration(self):
        """Calculate planned duration in days."""
        if self.start_date and self.expected_end_date:
            return (self.expected_end_date - self.start_date).days + 1
        return 0
    
    @property
    def actual_duration(self):
        """Calculate actual duration in days."""
        if self.actual_start_date and self.actual_end_date:
            return (self.actual_end_date.date() - self.actual_start_date.date()).days + 1
        elif self.actual_start_date and self.status == 'IN_PROGRESS':
            return (timezone.now().date() - self.actual_start_date.date()).days + 1
        return 0
    
    @property
    def duration_variance(self):
        """Calculate variance between planned and actual duration."""
        if self.actual_duration and self.planned_duration:
            return self.actual_duration - self.planned_duration
        return 0
    
    @property
    def progress_percentage(self):
        """Calculate maintenance progress percentage."""
        if self.status == 'COMPLETED':
            return 100
        elif self.status in ['CANCELLED', 'FAILED']:
            return 0
        elif self.status == 'IN_PROGRESS':
            if self.actual_start_date and self.expected_end_date:
                total_days = (self.expected_end_date - self.actual_start_date.date()).days
                elapsed_days = (timezone.now().date() - self.actual_start_date.date()).days
                if total_days > 0:
                    return min(int((elapsed_days / total_days) * 100), 99)
        return 0
    
    # Cost Properties
    @property
    def cost_variance(self):
        """Calculate cost variance (actual vs estimated)."""
        if self.actual_cost and self.estimated_cost:
            return self.actual_cost - self.estimated_cost
        return Decimal('0.00')
    
    @property
    def cost_variance_percentage(self):
        """Calculate cost variance as percentage."""
        if self.actual_cost and self.estimated_cost and self.estimated_cost > 0:
            variance = (self.cost_variance / self.estimated_cost) * 100
            return round(variance, 2)
        return Decimal('0.00')
    
    @property
    def total_cost(self):
        """Calculate total maintenance cost."""
        return (self.parts_cost or Decimal('0.00')) + (self.labor_cost or Decimal('0.00'))
    
    # Badge Methods for Templates
    def get_status_badge_class(self):
        """Return CSS class for status badge."""
        status_classes = {
            'SCHEDULED': 'badge bg-info',
            'IN_PROGRESS': 'badge bg-warning',
            'ON_HOLD': 'badge bg-secondary',
            'COMPLETED': 'badge bg-success',
            'CANCELLED': 'badge bg-dark',
            'FAILED': 'badge bg-danger',
        }
        return status_classes.get(self.status, 'badge bg-secondary')
    
    def get_priority_badge_class(self):
        """Return CSS class for priority badge."""
        priority_classes = {
            'LOW': 'badge bg-light text-dark',
            'MEDIUM': 'badge bg-info',
            'HIGH': 'badge bg-warning',
            'CRITICAL': 'badge bg-danger',
            'EMERGENCY': 'badge bg-dark',
        }
        return priority_classes.get(self.priority, 'badge bg-secondary')
    
    def get_type_badge_class(self):
        """Return CSS class for maintenance type badge."""
        type_classes = {
            'PREVENTIVE': 'badge bg-success',
            'CORRECTIVE': 'badge bg-warning',
            'EMERGENCY': 'badge bg-danger',
            'UPGRADE': 'badge bg-primary',
            'INSPECTION': 'badge bg-info',
            'CLEANING': 'badge bg-light text-dark',
            'CALIBRATION': 'badge bg-secondary',
            'REPLACEMENT': 'badge bg-warning',
            'WARRANTY': 'badge bg-success',
            'OTHER': 'badge bg-secondary',
        }
        return type_classes.get(self.maintenance_type, 'badge bg-secondary')
    
    # Utility Methods
    def can_be_started(self):
        """Check if maintenance can be started."""
        return (
            self.status == 'SCHEDULED' and
            self.is_active and
            (not self.requires_approval or (self.approved_by and self.approved_at))
        )
    
    def can_be_completed(self):
        """Check if maintenance can be completed."""
        return self.status == 'IN_PROGRESS' and self.is_active
    
    def can_be_cancelled(self):
        """Check if maintenance can be cancelled."""
        return self.status in ['SCHEDULED', 'ON_HOLD'] and self.is_active
    
    def can_be_rescheduled(self):
        """Check if maintenance can be rescheduled."""
        return self.status in ['SCHEDULED', 'ON_HOLD'] and self.is_active
    
    def get_next_maintenance_suggestion(self):
        """Suggest next maintenance date based on type and device."""
        if self.maintenance_type == 'PREVENTIVE':
            # Suggest quarterly preventive maintenance
            return self.start_date + timedelta(days=90)
        elif self.maintenance_type == 'INSPECTION':
            # Suggest annual inspection
            return self.start_date + timedelta(days=365)
        elif self.maintenance_type == 'CLEANING':
            # Suggest monthly cleaning for critical devices
            if self.device.priority == 'CRITICAL':
                return self.start_date + timedelta(days=30)
            else:
                return self.start_date + timedelta(days=90)
        else:
            # Default suggestion based on device type
            if hasattr(self.device, 'subcategory'):
                # Suggest based on device category
                return self.start_date + timedelta(days=180)
        
        return None
    
    @classmethod
    def get_maintenance_stats(cls):
        """Get maintenance statistics for dashboard."""
        total = cls.objects.count()
        active = cls.objects.filter(is_active=True).count()
        in_progress = cls.objects.filter(status='IN_PROGRESS').count()
        overdue = cls.objects.overdue().count()
        completed_this_month = cls.objects.filter(
            status='COMPLETED',
            actual_end_date__month=timezone.now().month,
            actual_end_date__year=timezone.now().year
        ).count()
        
        return {
            'total': total,
            'active': active,
            'in_progress': in_progress,
            'overdue': overdue,
            'completed_this_month': completed_this_month,
        }


# Signal handlers for automatic device status management
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Maintenance)
def maintenance_post_save(sender, instance, created, **kwargs):
    """Handle post-save operations for maintenance."""
    if created:
        # Log maintenance creation
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"New maintenance created: {instance.maintenance_id} for device {instance.device.device_id}")
        
        # Create notification for responsible users (implement as needed)
        # notify_maintenance_created(instance)

@receiver(post_delete, sender=Maintenance)
def maintenance_post_delete(sender, instance, **kwargs):
    """Handle post-delete operations for maintenance."""
    # Check if device needs status update after maintenance deletion
    try:
        other_active = Maintenance.objects.filter(
            device=instance.device,
            status__in=['SCHEDULED', 'IN_PROGRESS'],
            is_active=True
        ).exists()
        
        if not other_active and instance.device.status == 'MAINTENANCE':
            instance.device.status = 'AVAILABLE'
            instance.device.save(update_fields=['status'])
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating device status after maintenance deletion: {e}")