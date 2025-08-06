
from django.db import models
from django.core.validators import RegexValidator, EmailValidator, URLValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse


class VendorManager(models.Manager):
    """Custom manager for Vendor model."""
    
    def active(self):
        """Return only active vendors."""
        return self.filter(is_active=True)
    
    def by_type(self, vendor_type):
        """Filter vendors by type."""
        return self.filter(vendor_type=vendor_type)
    
    def service_providers(self):
        """Return vendors that provide services."""
        return self.filter(vendor_type__in=['MAINTENANCE', 'SUPPORT', 'INSTALLATION'])
    
    def suppliers(self):
        """Return vendors that supply products."""
        return self.filter(vendor_type__in=['SUPPLIER', 'MANUFACTURER'])


class Vendor(models.Model):
    """
    Model for managing vendor information in PIMS.
    
    This model stores comprehensive information about IT vendors, suppliers,
    service providers, and manufacturers that work with the Parliament Secretariat.
    """
    
    # Vendor Type Choices
    VENDOR_TYPE_CHOICES = [
        ('SUPPLIER', 'Equipment Supplier'),
        ('MANUFACTURER', 'Manufacturer'),
        ('MAINTENANCE', 'Maintenance Service Provider'),
        ('SUPPORT', 'Technical Support Provider'),
        ('INSTALLATION', 'Installation Service Provider'),
        ('CONSULTANT', 'IT Consultant'),
        ('OTHER', 'Other'),
    ]
    
    # Status Choices
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
        ('BLACKLISTED', 'Blacklisted'),
    ]
    
    # Validation patterns for Bangladeshi phone numbers
    phone_regex = RegexValidator(
        regex=r'^(\+880|880|0)?1[3-9]\d{8}$',
        message="Enter a valid Bangladeshi mobile number (11 digits starting with 01, e.g., 01712345678)"
    )
    
    # Basic Information
    vendor_code = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique vendor identification code (e.g., VND001, DELL001)',
        validators=[RegexValidator(
            regex=r'^[A-Z0-9]{3,20}$',
            message='Vendor code must be 3-20 characters, uppercase letters and numbers only.'
        )]
    )
    
    name = models.CharField(
        max_length=200,
        help_text='Full company/vendor name'
    )
    
    trade_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Trade name if different from company name'
    )
    
    vendor_type = models.CharField(
        max_length=20,
        choices=VENDOR_TYPE_CHOICES,
        default='SUPPLIER',
        help_text='Type of vendor or service provider'
    )
    
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text='Current vendor status'
    )
    
    # Contact Information
    contact_person = models.CharField(
        max_length=100,
        help_text='Primary contact person name'
    )
    
    contact_designation = models.CharField(
        max_length=100,
        blank=True,
        help_text='Designation of contact person (e.g., Sales Manager, Technical Lead)'
    )
    
    phone_primary = models.CharField(
        validators=[phone_regex],
        max_length=17,
        help_text='Primary contact phone number'
    )
    
    phone_secondary = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text='Secondary contact phone number'
    )
    
    email_primary = models.EmailField(
        help_text='Primary contact email address'
    )
    
    email_secondary = models.EmailField(
        blank=True,
        help_text='Secondary contact email address'
    )
    
    # Address Information
    address = models.TextField(
        help_text='Complete vendor address'
    )
    
    city = models.CharField(
        max_length=100,
        default='Dhaka',
        help_text='City where vendor is located'
    )
    
    district = models.CharField(
        max_length=100,
        default='Dhaka',
        help_text='District/State where vendor is located'
    )
    
    country = models.CharField(
        max_length=100,
        default='Bangladesh',
        help_text='Country where vendor is located'
    )
    
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text='Postal/ZIP code'
    )
    
    # Business Information
    business_registration_no = models.CharField(
        max_length=100,
        blank=True,
        help_text='Government business registration number'
    )
    
    tax_identification_no = models.CharField(
        max_length=100,
        blank=True,
        help_text='Tax identification number (TIN)'
    )
    
    website = models.URLField(
        blank=True,
        help_text='Company website URL'
    )
    
    # Service/Product Information
    specialization = models.TextField(
        blank=True,
        help_text='Areas of specialization or products/services offered'
    )
    
    service_categories = models.TextField(
        blank=True,
        help_text='Specific service categories (comma-separated)'
    )
    
    # Rating and Performance
    performance_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Performance rating out of 5.00'
    )
    
    # Additional Information
    notes = models.TextField(
        blank=True,
        help_text='Additional notes about the vendor'
    )
    
    # Status Management
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this vendor is currently active'
    )
    
    is_preferred = models.BooleanField(
        default=False,
        help_text='Designates whether this is a preferred vendor'
    )
    
    # Audit Fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Date and time when vendor was created'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Date and time when vendor was last updated'
    )
    
    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_vendors',
        help_text='User who created this vendor record'
    )
    
    updated_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_vendors',
        help_text='User who last updated this vendor record'
    )
    
    # Custom manager
    objects = VendorManager()
    
    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['name']
        indexes = [
            models.Index(fields=['vendor_code']),
            models.Index(fields=['name']),
            models.Index(fields=['vendor_type']),
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_preferred']),
            models.Index(fields=['city']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(performance_rating__gte=0) & models.Q(performance_rating__lte=5),
                name='vendors_performance_rating_range'
            )
        ]

    def __str__(self):
        """Return string representation of vendor."""
        return f"{self.vendor_code} - {self.name}"

    def get_absolute_url(self):
        """Return the absolute URL for this vendor."""
        return reverse('vendors:detail', kwargs={'pk': self.pk})

    def clean(self):
        """Perform custom validation."""
        super().clean()
        
        # Normalize vendor code to uppercase
        if self.vendor_code:
            self.vendor_code = self.vendor_code.upper().strip()
        
        # Validate performance rating
        if self.performance_rating is not None:
            if self.performance_rating < 0 or self.performance_rating > 5:
                raise ValidationError({
                    'performance_rating': 'Performance rating must be between 0 and 5.'
                })
        
        # Validate status logic
        if self.status == 'BLACKLISTED' and self.is_active:
            raise ValidationError({
                'is_active': 'Blacklisted vendors cannot be active.'
            })
        
        # Ensure contact information is provided for active vendors
        if self.is_active and self.status == 'ACTIVE':
            if not self.contact_person.strip():
                raise ValidationError({
                    'contact_person': 'Contact person is required for active vendors.'
                })
            if not self.phone_primary.strip():
                raise ValidationError({
                    'phone_primary': 'Primary phone number is required for active vendors.'
                })

    def save(self, *args, **kwargs):
        """Override save method for additional processing."""
        # Normalize data
        if self.vendor_code:
            self.vendor_code = self.vendor_code.upper().strip()
        if self.name:
            self.name = self.name.strip()
        if self.contact_person:
            self.contact_person = self.contact_person.strip()
        
        # Set status based on is_active field
        if not self.is_active and self.status == 'ACTIVE':
            self.status = 'INACTIVE'
        
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        """Return display name for UI purposes."""
        if self.trade_name and self.trade_name.strip():
            return f"{self.name} (T/A: {self.trade_name})"
        return self.name

    @property
    def full_address(self):
        """Return formatted full address."""
        address_parts = [self.address]
        if self.city:
            address_parts.append(self.city)
        if self.district and self.district != self.city:
            address_parts.append(self.district)
        if self.postal_code:
            address_parts.append(self.postal_code)
        if self.country:
            address_parts.append(self.country)
        
        return ', '.join(filter(None, address_parts))

    @property
    def primary_contact(self):
        """Return formatted primary contact information."""
        contact_info = []
        if self.contact_person:
            if self.contact_designation:
                contact_info.append(f"{self.contact_person} ({self.contact_designation})")
            else:
                contact_info.append(self.contact_person)
        
        if self.phone_primary:
            contact_info.append(f"Tel: {self.phone_primary}")
        
        if self.email_primary:
            contact_info.append(f"Email: {self.email_primary}")
        
        return ' | '.join(contact_info)

    def get_device_count(self):
        """
        Return the count of devices associated with this vendor.
        Note: This assumes devices have a vendor foreign key.
        """
        try:
            from devices.models import Device
            return Device.objects.filter(vendor=self).count()
        except ImportError:
            return 0

    def get_maintenance_count(self):
        """
        Return the count of maintenance records for this vendor.
        Note: This assumes maintenance has a vendor foreign key.
        """
        try:
            from maintenance.models import Maintenance
            return Maintenance.objects.filter(vendor=self).count()
        except ImportError:
            return 0

    def is_eligible_for_new_orders(self):
        """
        Check if vendor is eligible for new orders.
        """
        return (
            self.is_active and 
            self.status == 'ACTIVE' and
            self.contact_person.strip() and
            self.phone_primary.strip()
        )

    def get_service_categories_list(self):
        """
        Return service categories as a list.
        """
        if self.service_categories:
            return [cat.strip() for cat in self.service_categories.split(',') if cat.strip()]
        return []

    def get_vendor_type_display_icon(self):
        """
        Return Bootstrap icon class for vendor type.
        """
        icon_map = {
            'SUPPLIER': 'bi-shop',
            'MANUFACTURER': 'bi-building',
            'MAINTENANCE': 'bi-tools',
            'SUPPORT': 'bi-headset',
            'INSTALLATION': 'bi-gear',
            'CONSULTANT': 'bi-person-badge',
            'OTHER': 'bi-question-circle',
        }
        return icon_map.get(self.vendor_type, 'bi-building')

    def get_status_badge_class(self):
        """
        Return CSS class for status badge.
        """
        status_classes = {
            'ACTIVE': 'badge bg-success',
            'INACTIVE': 'badge bg-secondary',
            'SUSPENDED': 'badge bg-warning',
            'BLACKLISTED': 'badge bg-danger',
        }
        return status_classes.get(self.status, 'badge bg-secondary')