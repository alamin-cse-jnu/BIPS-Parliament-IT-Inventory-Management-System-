

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
    specific to Bangladesh Parliament Secretariat requirements.
    """
    
    # Employee Information
    employee_id = models.CharField(
        max_length=20, 
        unique=True,
        validators=[validate_employee_id],        
        help_text='Unique employee identification number (numbers only)'
    )
    
    designation = models.CharField(
        max_length=100,
        blank=True,
        help_text='Job designation/position in the Parliament Secretariat'
    )
    
    office = models.CharField(
        max_length=100,
        blank=True,
        help_text='Office within Bangladesh Parliament Secretariat'
    )
    
    # Contact Information
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'
            )
        ]
    )
    
    # Profile Information
    profile_image = models.ImageField(
        upload_to='user_images/',
        blank=True,
        null=True,
        validators=[validate_user_image],
        help_text='Profile picture for identification'
    )
    
    # Status and Metadata
    is_active_employee = models.BooleanField(
        default=True,
        help_text='Designates whether this user is an active employee'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional notes for administrative purposes
    notes = models.TextField(
        blank=True,
        help_text='Administrative notes about the user'
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['employee_id', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['office']),
            models.Index(fields=['is_active_employee']),
        ]

    def __str__(self):
        """String representation of the user."""
        if self.employee_id:
            return f"{self.employee_id} - {self.get_full_name()}"
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

    def save(self, *args, **kwargs):
        """
        Override save method to handle image resizing and validation.
        """
        # No need to convert employee_id to uppercase since it's numbers only
        super().save(*args, **kwargs)
        
        # Resize profile image if it exists
        if self.profile_image:
            self._resize_profile_image()

    def _resize_profile_image(self):
        """
        Resize profile image to maintain consistent dimensions and file size.
        """
        try:
            img = Image.open(self.profile_image.path)
            
            # Define maximum dimensions
            max_size = (300, 300)
            
            # Resize image while maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save the resized image
            img.save(self.profile_image.path, optimize=True, quality=85)
            
        except Exception as e:
            # Log the error but don't fail the save operation
            print(f"Error resizing profile image for user {self.username}: {e}")

    def get_display_name(self):
        """
        Return a formatted display name for UI purposes.
        """
        full_name = self.get_full_name()
        if self.employee_id and full_name != self.username:
            return f"{full_name} ({self.employee_id})"
        elif self.employee_id:
            return f"{self.username} ({self.employee_id})"
        return full_name

    def get_assigned_devices_count(self):
        """
        Return the count of devices currently assigned to this user.
        Note: This method assumes the Assignment model has a foreign key to User.
        """
        try:
            from assignments.models import Assignment
            return Assignment.objects.filter(
                assigned_to_user=self,
                is_active=True
            ).count()
        except ImportError:
            return 0

    def has_maintenance_permissions(self):
        """
        Check if user has permissions to manage maintenance records.
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