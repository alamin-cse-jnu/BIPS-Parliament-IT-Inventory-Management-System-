"""
Forms for Locations app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines forms for location management, creation, filtering, and search.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Building, Floor, Block, Room, Office, Location


class BuildingForm(forms.ModelForm):
    """
    Form for creating and editing Building records.
    """
    
    class Meta:
        model = Building
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter building name (e.g., Main Parliament Building)',
                'maxlength': 100
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter building code (e.g., MPB)',
                'maxlength': 10,
                'style': 'text-transform: uppercase;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter building description',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_code(self):
        """Validate and format building code."""
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper().strip()
            
            # Check for uniqueness (excluding current instance if editing)
            existing = Building.objects.filter(code=code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Building code already exists.')
        
        return code

    def clean_name(self):
        """Validate building name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            
            # Check for uniqueness (excluding current instance if editing)
            existing = Building.objects.filter(name__iexact=name)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Building name already exists.')
        
        return name


class FloorForm(forms.ModelForm):
    """
    Form for creating and editing Floor records.
    """
    
    class Meta:
        model = Floor
        fields = ['name', 'floor_number', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter floor name (e.g., Ground Floor, 1st Floor)',
                'maxlength': 50
            }),
            'floor_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter floor number (negative for basement)',
                'min': -10,
                'max': 50
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter floor description',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_name(self):
        """Validate and format floor name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
        return name


class BlockForm(forms.ModelForm):
    """
    Form for creating and editing Block records.
    """
    
    class Meta:
        model = Block
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter block name (e.g., East Block, West Wing)',
                'maxlength': 50
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter block code (e.g., EB, WW)',
                'maxlength': 10,
                'style': 'text-transform: uppercase;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter block description',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_code(self):
        """Validate and format block code."""
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper().strip()
        return code

    def clean_name(self):
        """Validate and format block name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
        return name


class RoomForm(forms.ModelForm):
    """
    Form for creating and editing Room records.
    """
    
    class Meta:
        model = Room
        fields = ['name', 'room_number', 'room_type', 'capacity', 'area_sqft', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter room name (e.g., Conference Room 1)',
                'maxlength': 100
            }),
            'room_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter room number (e.g., R-101)',
                'maxlength': 20
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter maximum capacity',
                'min': 1
            }),
            'area_sqft': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter area in square feet',
                'step': 0.01,
                'min': 0
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter room description',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_room_number(self):
        """Validate and format room number."""
        room_number = self.cleaned_data.get('room_number')
        if room_number:
            room_number = room_number.strip()
        return room_number

    def clean_name(self):
        """Validate and format room name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
        return name


class OfficeForm(forms.ModelForm):
    """
    Form for creating and editing Office records.
    """
    
    class Meta:
        model = Office
        fields = ['name', 'office_code', 'office_type', 'head_of_office', 'contact_number', 'email', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter office name (e.g., IT Department)',
                'maxlength': 100
            }),
            'office_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter office code (e.g., IT-001)',
                'maxlength': 20,
                'style': 'text-transform: uppercase;'
            }),
            'office_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'head_of_office': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter name of officer in charge',
                'maxlength': 100
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact number',
                'maxlength': 20
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter official email address'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter office description and responsibilities',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_office_code(self):
        """Validate and format office code."""
        office_code = self.cleaned_data.get('office_code')
        if office_code:
            office_code = office_code.upper().strip()
            
            # Check for uniqueness (excluding current instance if editing)
            existing = Office.objects.filter(office_code=office_code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Office code already exists.')
        
        return office_code

    def clean_name(self):
        """Validate and format office name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
        return name


class LocationForm(forms.ModelForm):
    """
    Form for creating and editing Location records with comprehensive validation.
    """
    
    class Meta:
        model = Location
        fields = [
            'name', 'location_code', 'address',
            'building', 'floor', 'block', 'room', 'office',
            'latitude', 'longitude', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter location name',
                'maxlength': 200
            }),
            'location_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter unique location code (e.g., LOC-001)',
                'maxlength': 50,
                'style': 'text-transform: uppercase;'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full address or location description',
                'rows': 3
            }),
            'building': forms.Select(attrs={
                'class': 'form-select'
            }),
            'floor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'block': forms.Select(attrs={
                'class': 'form-select'
            }),
            'room': forms.Select(attrs={
                'class': 'form-select'
            }),
            'office': forms.Select(attrs={
                'class': 'form-select'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter latitude (-90 to 90)',
                'step': 0.00000001,
                'min': -90,
                'max': 90
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter longitude (-180 to 180)',
                'step': 0.00000001,
                'min': -180,
                'max': 180
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter additional notes about this location',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add empty option to foreign key fields
        self.fields['building'].empty_label = "Select Building (Optional)"
        self.fields['floor'].empty_label = "Select Floor (Optional)"
        self.fields['block'].empty_label = "Select Block (Optional)"
        self.fields['room'].empty_label = "Select Room (Optional)"
        self.fields['office'].empty_label = "Select Office (Optional)"
        
        # Filter only active records for foreign key choices
        self.fields['building'].queryset = Building.objects.filter(is_active=True)
        self.fields['floor'].queryset = Floor.objects.filter(is_active=True)
        self.fields['block'].queryset = Block.objects.filter(is_active=True)
        self.fields['room'].queryset = Room.objects.filter(is_active=True)
        self.fields['office'].queryset = Office.objects.filter(is_active=True)

    def clean_location_code(self):
        """Validate and format location code."""
        location_code = self.cleaned_data.get('location_code')
        if location_code:
            location_code = location_code.upper().strip()
            
            # Check for uniqueness (excluding current instance if editing)
            existing = Location.objects.filter(location_code=location_code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Location code already exists.')
        
        return location_code

    def clean_name(self):
        """Validate and format location name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
        return name

    def clean(self):
        """
        Custom validation to ensure at least one location component is selected
        and validate geo-coordinates.
        """
        cleaned_data = super().clean()
        
        # Get location components
        building = cleaned_data.get('building')
        floor = cleaned_data.get('floor')
        block = cleaned_data.get('block')
        room = cleaned_data.get('room')
        office = cleaned_data.get('office')
        
        # Check if at least one location component is selected
        if not any([building, floor, block, room, office]):
            raise ValidationError(
                'At least one location component must be selected (Building, Floor, Block, Room, or Office).'
            )
        
        # Validate geo-coordinates
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        # Both coordinates must be provided together or both left empty
        if (latitude is None) != (longitude is None):
            raise ValidationError(
                'Both latitude and longitude must be provided together, or both left empty.'
            )
        
        return cleaned_data


class LocationSearchForm(forms.Form):
    """
    Form for searching and filtering locations.
    """
    
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, code, or address...',
            'autocomplete': 'off'
        })
    )
    
    building = forms.ModelChoiceField(
        queryset=Building.objects.filter(is_active=True),
        required=False,
        empty_label="All Buildings",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    floor = forms.ModelChoiceField(
        queryset=Floor.objects.filter(is_active=True),
        required=False,
        empty_label="All Floors",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    block = forms.ModelChoiceField(
        queryset=Block.objects.filter(is_active=True),
        required=False,
        empty_label="All Blocks",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    room_type = forms.ChoiceField(
        choices=[('', 'All Room Types')] + Room.ROOM_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    office_type = forms.ChoiceField(
        choices=[('', 'All Office Types')] + Office.OFFICE_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    has_coordinates = forms.ChoiceField(
        choices=[
            ('', 'All Locations'),
            ('yes', 'With GPS Coordinates'),
            ('no', 'Without GPS Coordinates')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('true', 'Active Only'),
            ('false', 'Inactive Only')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    def filter_queryset(self, queryset):
        """
        Apply filters to the queryset based on form data.
        """
        if not self.is_valid():
            return queryset

        # Search filter
        search = self.cleaned_data.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(location_code__icontains=search) |
                Q(address__icontains=search) |
                Q(building__name__icontains=search) |
                Q(building__code__icontains=search) |
                Q(floor__name__icontains=search) |
                Q(block__name__icontains=search) |
                Q(block__code__icontains=search) |
                Q(room__name__icontains=search) |
                Q(room__room_number__icontains=search) |
                Q(office__name__icontains=search) |
                Q(office__office_code__icontains=search) |
                Q(notes__icontains=search)
            )

        # Building filter
        building = self.cleaned_data.get('building')
        if building:
            queryset = queryset.filter(building=building)

        # Floor filter
        floor = self.cleaned_data.get('floor')
        if floor:
            queryset = queryset.filter(floor=floor)

        # Block filter
        block = self.cleaned_data.get('block')
        if block:
            queryset = queryset.filter(block=block)

        # Room type filter
        room_type = self.cleaned_data.get('room_type')
        if room_type:
            queryset = queryset.filter(room__room_type=room_type)

        # Office type filter
        office_type = self.cleaned_data.get('office_type')
        if office_type:
            queryset = queryset.filter(office__office_type=office_type)

        # Coordinates filter
        has_coordinates = self.cleaned_data.get('has_coordinates')
        if has_coordinates == 'yes':
            queryset = queryset.filter(
                latitude__isnull=False,
                longitude__isnull=False
            )
        elif has_coordinates == 'no':
            queryset = queryset.filter(
                Q(latitude__isnull=True) | Q(longitude__isnull=True)
            )

        # Active status filter
        is_active = self.cleaned_data.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset


class BulkLocationActionForm(forms.Form):
    """
    Form for performing bulk actions on multiple locations.
    """
    
    ACTION_CHOICES = [
        ('activate', 'Mark as Active'),
        ('deactivate', 'Mark as Inactive'),
        ('export_coordinates', 'Export GPS Coordinates'),
        ('delete', 'Delete Selected')
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    location_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    confirm = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    def clean_location_ids(self):
        """Validate location IDs."""
        location_ids = self.cleaned_data.get('location_ids')
        if location_ids:
            try:
                ids = [int(id.strip()) for id in location_ids.split(',') if id.strip()]
                # Verify all IDs exist
                valid_ids = Location.objects.filter(id__in=ids).values_list('id', flat=True)
                if len(valid_ids) != len(ids):
                    raise ValidationError('Some selected locations are invalid.')
                return list(valid_ids)
            except (ValueError, TypeError):
                raise ValidationError('Invalid location IDs provided.')
        return []


class CoordinateInputForm(forms.Form):
    """
    Standalone form for inputting GPS coordinates.
    """
    
    latitude = forms.DecimalField(
        max_digits=10,
        decimal_places=8,
        min_value=-90.0,
        max_value=90.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter latitude (-90 to 90)',
            'step': 0.00000001
        })
    )
    
    longitude = forms.DecimalField(
        max_digits=11,
        decimal_places=8,
        min_value=-180.0,
        max_value=180.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter longitude (-180 to 180)',
            'step': 0.00000001
        })
    )

    def clean(self):
        """Validate coordinate pair."""
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if latitude is not None and longitude is not None:
            # Additional validation for Bangladesh coordinates if needed
            # Bangladesh is approximately between 20.670883 to 26.446526 N latitude
            # and 88.025889 to 92.680774 E longitude
            if not (20.0 <= latitude <= 27.0):
                self.add_error('latitude', 'Latitude should be within Bangladesh boundaries (20-27 degrees N).')
            
            if not (88.0 <= longitude <= 93.0):
                self.add_error('longitude', 'Longitude should be within Bangladesh boundaries (88-93 degrees E).')
        
        return cleaned_data