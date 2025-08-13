from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import os
from django.urls import reverse

class Building(models.Model):
    """
    Model for managing buildings within Bangladesh Parliament Secretariat.
    
    Each building represents a distinct physical structure within the 
    Parliament complex.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Name of the building (e.g., Main Parliament Building, Secretariat Building)'
    )
    
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text='Short code for the building (e.g., MPB, SB)'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Additional description about the building'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this building is currently in use'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Building'
        verbose_name_plural = 'Buildings'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        """Custom validation for building."""
        if self.code:
            self.code = self.code.upper().strip()


class Floor(models.Model):
    """
    Model for managing floors within buildings.
    
    Represents different floor levels within any building structure.
    """
    name = models.CharField(
        max_length=50,
        help_text='Floor name or number (e.g., Ground Floor, 1st Floor, Basement)'
    )
    
    floor_number = models.IntegerField(
        validators=[MinValueValidator(-10), MaxValueValidator(50)],
        help_text='Numeric representation of floor level (negative for basement)'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Description of what this floor contains'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this floor is currently accessible'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Floor'
        verbose_name_plural = 'Floors'
        ordering = ['floor_number']
        indexes = [
            models.Index(fields=['floor_number']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} (Level {self.floor_number})"

    def clean(self):
        """Custom validation for floor."""
        if self.name:
            self.name = self.name.strip()


class Block(models.Model):
    """
    Model for managing blocks or sections within floors.
    
    Represents different sections, wings, or blocks that help organize
    spaces within the Parliament complex.
    """
    name = models.CharField(
        max_length=50,
        help_text='Block name or designation (e.g., East Block, West Wing, Section A)'
    )
    
    code = models.CharField(
        max_length=10,
        help_text='Short code for the block (e.g., EB, WW, SA)'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Description of the block and its purpose'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this block is currently in use'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Block'
        verbose_name_plural = 'Blocks'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        """Custom validation for block."""
        if self.code:
            self.code = self.code.upper().strip()
        if self.name:
            self.name = self.name.strip()


class Room(models.Model):
    """
    Model for managing individual rooms.
    
    Represents specific rooms that can house equipment, people, or serve
    specific functions within the Parliament Secretariat.
    """
    ROOM_TYPES = [
        ('office', 'Office'),
        ('meeting', 'Meeting Room'),
        ('storage', 'Storage'),
        ('server', 'Server Room'),
        ('Data Center', 'Data Center Room'),
        ('conference', 'Conference Room'),
        ('hall', 'Hall'),
        ('oath', 'Oath Room'),
        ('chamber', 'Chamber'),
        ('lobby', 'Lobby'),
        ('utility', 'Utility Room'),
        ('washroom', 'WashRoom'),
        ('pantry', 'Pantry Room'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text='Room name or number (e.g., Conference Room 1, Server Room A)'
    )
    
    room_number = models.CharField(
        max_length=20,
        help_text='Official room number or identifier'
    )
    
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPES,
        default='office',
        help_text='Type or category of the room'
    )
    
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum capacity of people/equipment this room can hold'
    )
    
    area_sqft = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Area of the room in square feet'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Description of the room and its current use'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this room is currently available for use'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'
        ordering = ['room_number', 'name']
        indexes = [
            models.Index(fields=['room_number']),
            models.Index(fields=['room_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.room_number} - {self.name}"

    def clean(self):
        """Custom validation for room."""
        if self.room_number:
            self.room_number = self.room_number.strip()
        if self.name:
            self.name = self.name.strip()


class Office(models.Model):
    """
    Model for managing specific offices or administrative units.
    
    Represents departmental offices, individual officer cabins, or
    administrative units within the Parliament Secretariat.
    """
    OFFICE_TYPES = [
        ('wing', 'Wing Office'),
        ('branch', 'Branch Office'),
        ('section', 'Section Office'),
        ('secretary', 'Secretary Office'),
        ('speaker', 'Speaker Office'),
        ('deputy speaker', 'Deputy Speaker Office'),
        ('chief Whip', 'Chief Whip Office'),
        ('whip', 'Whip Office'),
        ('chairman', 'SC Chairman Office'),
        ('mp', 'MP Office'),
        ('unit', 'Unit'),
        ('store', 'Store Office'),
        ('project', 'Project Office'),       
        ('other', 'Other'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text='Office name (e.g., IT Department, Secretary Office)'
    )
    
    office_code = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique office code (e.g., IT-001, SEC-001)'
    )
    
    office_type = models.CharField(
        max_length=20,
        choices=OFFICE_TYPES,
        default='department',
        help_text='Type of administrative office'
    )
    
    head_of_office = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name of the officer in charge'
    )
    
    contact_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='Official contact number for this office'
    )
    
    email = models.EmailField(
        blank=True,
        help_text='Official email address'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Description of office functions and responsibilities'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this office is currently operational'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Office'
        verbose_name_plural = 'Offices'
        ordering = ['office_code', 'name']
        indexes = [
            models.Index(fields=['office_code']),
            models.Index(fields=['office_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.office_code} - {self.name}"

    def clean(self):
        """Custom validation for office."""
        if self.office_code:
            self.office_code = self.office_code.upper().strip()
        if self.name:
            self.name = self.name.strip()


class Location(models.Model):
    """
    Comprehensive location model combining all location components with geo-coordinates.
    
    This model acts as the final location entity that can reference any combination
    of Building, Floor, Block, Room, and Office. Only this model stores geo-coordinates
    as it represents the ultimate physical location.
    """
    
    # Optional Foreign Keys - No dependencies between components
    building = models.ForeignKey(
        Building,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Associated building (optional)'
    )
    
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Associated floor (optional)'
    )
    
    block = models.ForeignKey(
        Block,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Associated block or section (optional)'
    )
    
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Associated room (optional)'
    )
    
    office = models.ForeignKey(
        Office,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Associated office (optional)'
    )
    
    # Geo-coordinates (only stored in Location model)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-90.0),
            MaxValueValidator(90.0)
        ],
        help_text='Latitude coordinate (-90 to 90 degrees)'
    )
    
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-180.0),
            MaxValueValidator(180.0)
        ],
        help_text='Longitude coordinate (-180 to 180 degrees)'
    )
    
    # Location identification
    name = models.CharField(
        max_length=200,
        help_text='Human-readable location name'
    )
    
    location_code = models.CharField(
        max_length=50,
        unique=True,
        help_text='Unique location identifier code'
    )
    
    # Additional location details
    address = models.TextField(
        blank=True,
        help_text='Full address or location description'
    )
    
    notes = models.TextField(
        blank=True,
        help_text='Additional notes about this location'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this location is currently active'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['location_code', 'name']
        indexes = [
            models.Index(fields=['location_code']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['is_active']),
            models.Index(fields=['building']),
            models.Index(fields=['office']),
        ]

    def __str__(self):
        return f"{self.location_code} - {self.name}"

    def clean(self):
        """
        Custom validation to ensure at least one location component is referenced
        and validate geo-coordinates if provided.
        """
        # Ensure at least one foreign key reference exists
        if not any([self.building, self.floor, self.block, self.room, self.office]):
            raise ValidationError(
                'Location must reference at least one of: Building, Floor, Block, Room, or Office.'
            )
        
        # Validate geo-coordinates are both provided or both empty
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError(
                'Both latitude and longitude must be provided together, or both left empty.'
            )
        
        # Clean and format codes/names
        if self.location_code:
            self.location_code = self.location_code.upper().strip()
        if self.name:
            self.name = self.name.strip()

    def save(self, *args, **kwargs):
        """Override save to run clean validation."""
        self.clean()
        super().save(*args, **kwargs)

    def get_full_location_description(self):
        """
        Generate a comprehensive description of the location based on
        all associated location components.
        """
        parts = []
        
        if self.building:
            parts.append(f"Building: {self.building.name}")
        if self.floor:
            parts.append(f"Floor: {self.floor.name}")
        if self.block:
            parts.append(f"Block: {self.block.name}")
        if self.room:
            parts.append(f"Room: {self.room.name}")
        if self.office:
            parts.append(f"Office: {self.office.name}")
        
        return " | ".join(parts) if parts else self.name

    def has_coordinates(self):
        """Check if location has geo-coordinates."""
        return self.latitude is not None and self.longitude is not None

    def get_coordinates(self):
        """Return coordinates as tuple or None."""
        if self.has_coordinates():
            return (float(self.latitude), float(self.longitude))
        return None

    @property
    def coordinate_string(self):
        """Return formatted coordinate string for display."""
        if self.has_coordinates():
            return f"{self.latitude}, {self.longitude}"
        return "No coordinates"

    def get_related_components(self):
        """Return a dictionary of all related location components."""
        return {
            'building': self.building,
            'floor': self.floor,
            'block': self.block,
            'room': self.room,
            'office': self.office,
        }

    @classmethod
    def get_available_locations(cls):
        """Return all active locations."""
        return cls.objects.filter(is_active=True)

    @classmethod
    def get_locations_with_coordinates(cls):
        """Return all locations that have geo-coordinates."""
        return cls.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            is_active=True
        )

class LocationQRCode(models.Model):
    """
    QR codes for location identification and tracking.
    Generated automatically when locations are created or updated.
    Follows the same pattern as Device QRCode model for consistency.
    """
    
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='qr_codes',
        help_text="Location this QR code represents"
    )
    
    # QR Code Details
    qr_code_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text="Unique QR code identifier"
    )
    qr_code = models.ImageField(
        upload_to='qrcodes/locations/',
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
        db_table = 'locations_locationqrcode'
        verbose_name = 'Location QR Code'
        verbose_name_plural = 'Location QR Codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['location', 'is_active']),
            models.Index(fields=['qr_code_id']),
        ]
    
    def __str__(self):
        return f"QR Code for {self.location.name}"
    
    def save(self, *args, **kwargs):
        # Deactivate other QR codes for this location
        if self.is_active:
            LocationQRCode.objects.filter(location=self.location, is_active=True).exclude(
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
        return reverse('locations:qr_download', kwargs={'pk': self.pk})
    
    @property
    def file_exists(self):
        """Check if QR code file exists."""
        return self.qr_code and os.path.isfile(self.qr_code.path)