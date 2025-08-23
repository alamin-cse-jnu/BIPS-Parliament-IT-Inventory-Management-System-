from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from PIL import Image
import os
from pims.utils.validators import validate_user_image, validate_employee_id


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser for PIMS.
    
    Adds additional fields for employee information and profile management
    specific to Bangladesh Parliament Secretariat temblanrequirements.
    
    PRP Integration: This model supports one-way sync from PRP (Parliament Resource Portal)
    where PRP serves as the authoritative source for user data.
    """
    
    # ========================================================================
    # EMPLOYEE INFORMATION FIELDS
    # ========================================================================
    # Note: These fields are reused for PRP data mapping - DO NOT MODIFY
    
    employee_id = models.CharField(
        max_length=20, 
        unique=True,
        validators=[validate_employee_id],        
        help_text='Unique employee identification number (numbers only). For PRP users: maps to PRP userId'
    )
    
    designation = models.CharField(
        max_length=100,
        blank=True,
        help_text='Job designation/position in the Parliament Secretariat. For PRP users: maps to PRP designationEng'
    )
    
    office = models.CharField(
        max_length=100,
        blank=True,
        help_text='Office within Bangladesh Parliament Secretariat. For PRP users: maps to PRP department nameEng'
    )
    
    # ========================================================================
    # CONTACT INFORMATION FIELDS
    # ========================================================================
    # Note: These fields are reused for PRP data mapping - DO NOT MODIFY
    
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'
            )
        ],
        help_text='Contact phone number. For PRP users: maps to PRP mobile'
    )
    
    # ========================================================================
    # PROFILE INFORMATION FIELDS
    # ========================================================================
    # Note: These fields are reused for PRP data mapping - DO NOT MODIFY
    
    profile_image = models.ImageField(
        upload_to='user_images/',
        blank=True,
        null=True,
        validators=[validate_user_image],
        help_text='Profile picture for identification. For PRP users: converted from PRP photo'
    )
    
    # ========================================================================
    # STATUS AND METADATA FIELDS
    # ========================================================================
    # Note: These fields are reused for PRP data mapping - DO NOT MODIFY
    
    is_active_employee = models.BooleanField(
        default=True,
        help_text='Designates whether this user is an active employee. For PRP users: maps to PRP status'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional notes for administrative purposes
    notes = models.TextField(
        blank=True,
        help_text='Administrative notes about the user'
    )
    
    # ========================================================================
    # PRP INTEGRATION TRACKING FIELDS
    # ========================================================================
    
    is_prp_managed = models.BooleanField(
        default=False,
        help_text='Indicates if this user is managed by PRP (Parliament Resource Portal). '
                  'PRP-managed users have read-only data that syncs from PRP API.'
    )
    
    prp_last_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of the last successful sync from PRP API. '
                  'Only applicable for PRP-managed users (is_prp_managed=True).'
    )

    class Meta:
        db_table = 'users_customuser'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['employee_id', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['office']),
            models.Index(fields=['is_active_employee']),
            models.Index(fields=['is_prp_managed']),
            models.Index(fields=['is_prp_managed', 'prp_last_sync']),
        ]

    def __str__(self):
        """String representation of the user."""
        if self.employee_id:
            prp_indicator = " [PRP]" if self.is_prp_managed else ""
            return f"{self.employee_id} - {self.get_full_name()}{prp_indicator}"
        return self.get_full_name() or self.username

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.username

    def get_display_name(self):
        """
        Return the most appropriate display name for the user.
        Priority: Full name > Username > Employee ID
        """
        full_name = self.get_full_name()
        if full_name:
            return full_name
        elif self.username:
            return self.username
        elif self.employee_id:
            return f"Employee #{self.employee_id}"
        else:
            return "Unknown User"

    def get_initials(self):
        """
        Return initials from first and last name.
        Falls back to first two characters of username if no names available.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[:2].upper()
        elif self.username:
            return self.username[:2].upper()
        else:
            return "??"

    def save(self, *args, **kwargs):
        """
        Override save method to handle image resizing and PRP sync tracking.
        """
        # Handle profile image resizing
        if self.profile_image:
            try:
                img = Image.open(self.profile_image.path)
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size, Image.Resampling.LANCZOS)
                    img.save(self.profile_image.path, optimize=True, quality=85)
            except (AttributeError, FileNotFoundError) as e:
                print(f"Error resizing profile image for user {self.username}: {e}")
        
        # Update sync timestamp for PRP users when data changes
        if self.is_prp_managed and self.pk:
            # Placeholder for future sync logic
            pass
            
        super().save(*args, **kwargs)

    def get_assigned_devices_count(self):
        """
        Get count of currently assigned devices to this user.
        Uses try-except to handle cases where assignments app might not be available.
        """
        try:
            from assignments.models import Assignment
            return Assignment.objects.filter(
                assigned_to=self,
                is_active=True,
                status='ASSIGNED'
            ).count()
        except ImportError:
            return 0

    def get_assigned_devices(self):
        """
        Get list of currently assigned devices.
        """
        try:
            from assignments.models import Assignment
            assignments = Assignment.objects.filter(
                assigned_to=self,
                is_active=True,
                status='ASSIGNED'
            ).select_related('device')
            return [assignment.device for assignment in assignments]
        except ImportError:
            return []

    def get_assignment_history(self, limit=10):
        """
        Get recent assignment history for this user.
        """
        try:
            from assignments.models import Assignment
            return Assignment.objects.filter(
                assigned_to=self
            ).select_related('device', 'assigned_location').order_by('-assigned_date')[:limit]
        except ImportError:
            return []

    def has_overdue_assignments(self):
        """
        Check if user has any overdue assignments.
        """
        try:
            from assignments.models import Assignment
            return Assignment.objects.filter(
                assigned_to=self,
                status='ASSIGNED',
                expected_return_date__lt=timezone.now().date()
            ).exists()
        except ImportError:
            return False

    def can_be_assigned_device(self):
        """
        Check if user can be assigned new devices.
        Business rule: Active employees can be assigned devices.
        """
        return self.is_active and self.is_active_employee

    def has_device_permissions(self):
        """
        Check if user has permissions to manage devices.
        """
        return (
            self.is_superuser or 
            self.has_perm('devices.add_device') or
            self.has_perm('devices.change_device') or
            self.has_perm('devices.view_device')
        )

    def has_user_management_permissions(self):
        """
        Check if user has permissions to manage other users.
        """
        return (
            self.is_superuser or 
            self.has_perm('auth.add_user') or
            self.has_perm('auth.change_user')
        )

    def has_maintenance_permissions(self):
        """
        Check if user has permissions to manage device maintenance.
        """
        return (
            self.is_superuser or 
            self.has_perm('maintenance.add_maintenance') or
            self.has_perm('maintenance.change_maintenance')
        )

    def has_assignment_permissions(self):
        """
        Check if user has permissions to manage device assignments.
        """
        return (
            self.is_superuser or 
            self.has_perm('assignments.add_assignment') or
            self.has_perm('assignments.change_assignment')
        )

    def can_generate_reports(self):
        """
        Check if user has permissions to generate reports.
        """
        return (
            self.is_superuser or 
            self.has_perm('devices.view_device') or
            self.groups.filter(name__icontains='admin').exists()
        )

    def is_prp_user(self):
        """
        Check if this user is managed by PRP.
        Convenience method for template usage.
        """
        return self.is_prp_managed

    def get_prp_sync_status(self):
        """
        Get human-readable PRP sync status.
        """
        if not self.is_prp_managed:
            return "Not PRP Managed"
        
        if self.prp_last_sync is None:
            return "Never Synced"
        
        # Calculate time since last sync
        now = timezone.now()
        time_diff = now - self.prp_last_sync
        
        if time_diff.days > 7:
            return f"Last synced {time_diff.days} days ago"
        elif time_diff.days > 0:
            return f"Last synced {time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            return f"Last synced {hours} hour{'s' if hours > 1 else ''} ago"
        else:
            return "Recently synced"

    def can_edit_prp_fields(self):
        """
        Check if PRP-sourced fields can be edited.
        Business Rule: PRP-managed users have read-only fields from PRP.
        """
        return not self.is_prp_managed

    def get_prp_readonly_fields(self):
        """
        Get list of fields that should be read-only for PRP users.
        These fields are populated from PRP API and should not be editable.
        """
        if not self.is_prp_managed:
            return []
        
        return [
            'employee_id',      # PRP userId
            'first_name',       # PRP nameEng (split)
            'last_name',        # PRP nameEng (split)  
            'email',            # PRP email
            'designation',      # PRP designationEng
            'office',           # PRP department nameEng
            'phone_number',     # PRP mobile
            'profile_image',    # PRP photo (converted)
            # Note: is_active_employee can be overridden by PIMS admin
        ]

    def mark_prp_sync(self):
        """
        Mark this user as successfully synced from PRP.
        Updates the prp_last_sync timestamp.
        """
        self.prp_last_sync = timezone.now()
        self.save(update_fields=['prp_last_sync'])

    @classmethod
    def get_active_employees(cls):
        """
        Return queryset of active employees.
        """
        return cls.objects.filter(
            is_active=True,
            is_active_employee=True
        )

    @classmethod
    def get_by_employee_id(cls, employee_id):
        """
        Get user by employee ID.
        """
        try:
            return cls.objects.get(employee_id=str(employee_id))
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_prp_users(cls):
        """
        Return queryset of PRP-managed users.
        """
        return cls.objects.filter(is_prp_managed=True)

    @classmethod
    def get_non_prp_users(cls):
        """
        Return queryset of non-PRP users (locally managed).
        """
        return cls.objects.filter(is_prp_managed=False)

    @classmethod
    def get_prp_user_by_employee_id(cls, employee_id):
        """
        Get PRP user by employee ID (PRP userId).
        """
        try:
            return cls.objects.get(
                employee_id=str(employee_id),
                is_prp_managed=True
            )
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_users_needing_sync(cls, hours_threshold=24):
        """
        Get PRP users that need syncing based on time threshold.
        
        Args:
            hours_threshold (int): Hours since last sync to consider for re-sync
        
        Returns:
            QuerySet: PRP users that need syncing
        """
        threshold_time = timezone.now() - timezone.timedelta(hours=hours_threshold)
        
        return cls.objects.filter(
            is_prp_managed=True
        ).filter(
            models.Q(prp_last_sync__isnull=True) |  # Never synced
            models.Q(prp_last_sync__lt=threshold_time)  # Last sync too old
        )