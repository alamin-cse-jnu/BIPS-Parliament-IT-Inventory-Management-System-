
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Vendor


class VendorForm(forms.ModelForm):
    """
    Form for creating and editing Vendor records.
    Enhanced with better validation and error handling.
    """
    
    class Meta:
        model = Vendor
        fields = [
            'vendor_code', 'name', 'trade_name', 'vendor_type', 'status',
            'contact_person', 'contact_designation',
            'phone_primary', 'phone_secondary',
            'email_primary', 'email_secondary',
            'address', 'city', 'district', 'country', 'postal_code',
            'business_registration_no', 'tax_identification_no', 'website',
            'specialization', 'service_categories',
            'performance_rating', 'is_preferred', 'is_active', 'notes'
        ]
        
        widgets = {
            'vendor_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter vendor code (e.g., VND001, DELL001)',
                'maxlength': 20,
                'style': 'text-transform: uppercase;',
                'required': True
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full company/vendor name',
                'maxlength': 200,
                'required': True
            }),
            'trade_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter trade name (if different from company name)',
                'maxlength': 200
            }),
            'vendor_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter primary contact person name',
                'maxlength': 100,
                'required': True
            }),
            'contact_designation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact person designation',
                'maxlength': 100
            }),
            'phone_primary': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+880 1XXX-XXXXXX',
                'maxlength': 20,
                'required': True
            }),
            'phone_secondary': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+880 1XXX-XXXXXX (Optional)',
                'maxlength': 20
            }),
            'email_primary': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'primary@vendor.com'
            }),
            'email_secondary': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'secondary@vendor.com (Optional)'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter complete address',
                'rows': 3
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dhaka',
                'maxlength': 100
            }),
            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dhaka',
                'maxlength': 100
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bangladesh',
                'maxlength': 100,
                'value': 'Bangladesh'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1000',
                'maxlength': 20
            }),
            'business_registration_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business registration number',
                'maxlength': 50
            }),
            'tax_identification_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tax identification number',
                'maxlength': 50
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.vendor.com'
            }),
            'specialization': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe vendor specialization and expertise',
                'rows': 3
            }),
            'service_categories': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'List service categories (e.g., Hardware, Software, Support)',
                'rows': 2
            }),
            'performance_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '3.5',
                'min': 0,
                'max': 5,
                'step': 0.1
            }),
            'is_preferred': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Additional notes about this vendor',
                'rows': 4
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values
        self.fields['is_active'].initial = True
        self.fields['status'].initial = 'ACTIVE'
        self.fields['country'].initial = 'Bangladesh'
        
        # Add help text
        self.fields['vendor_code'].help_text = 'Unique identifier for this vendor (e.g., DELL001, MS001)'
        self.fields['performance_rating'].help_text = 'Rate vendor performance from 0.0 to 5.0'
        self.fields['phone_primary'].help_text = 'Bangladesh phone format: +880 1XXX-XXXXXX'

    def clean_vendor_code(self):
        """Validate vendor code uniqueness and format."""
        vendor_code = self.cleaned_data.get('vendor_code', '').upper().strip()
        
        if not vendor_code:
            raise ValidationError('Vendor code is required.')
        
        # Check format
        if len(vendor_code) < 3:
            raise ValidationError('Vendor code must be at least 3 characters long.')
        
        if not vendor_code.replace('_', '').replace('-', '').isalnum():
            raise ValidationError('Vendor code can only contain letters, numbers, hyphens, and underscores.')
        
        # Check uniqueness
        queryset = Vendor.objects.filter(vendor_code=vendor_code)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(f'Vendor code "{vendor_code}" already exists. Please choose a different code.')
        
        return vendor_code

    def clean_name(self):
        """Validate vendor name."""
        name = self.cleaned_data.get('name', '').strip()
        
        if not name:
            raise ValidationError('Vendor name is required.')
        
        if len(name) < 2:
            raise ValidationError('Vendor name must be at least 2 characters long.')
        
        return name

    def clean_contact_person(self):
        """Validate contact person name."""
        contact_person = self.cleaned_data.get('contact_person', '').strip()
        
        if not contact_person:
            raise ValidationError('Contact person is required.')
        
        if len(contact_person) < 2:
            raise ValidationError('Contact person name must be at least 2 characters long.')
        
        return contact_person

    def clean_phone_primary(self):
        """Validate primary phone number."""
        phone = self.cleaned_data.get('phone_primary', '').strip()
        
        if not phone:
            raise ValidationError('Primary phone number is required.')
        
        # Bangladesh phone number validation
        import re
        # Remove spaces, hyphens for validation
        clean_phone = re.sub(r'[\s\-]', '', phone)
        
        # Bangladesh phone pattern: +880, 880, or 0 followed by 1-9 and 8-10 more digits
        bd_phone_pattern = r'^(\+880|880|0)?[1-9]\d{8,10}$'
        
        if not re.match(bd_phone_pattern, clean_phone):
            raise ValidationError(
                'Please enter a valid Bangladesh phone number. '
                'Format: +880 1XXX-XXXXXX or 01XXX-XXXXXX'
            )
        
        return phone

    def clean_phone_secondary(self):
        """Validate secondary phone number if provided."""
        phone = self.cleaned_data.get('phone_secondary', '').strip()
        
        if phone:  # Only validate if provided
            import re
            clean_phone = re.sub(r'[\s\-]', '', phone)
            bd_phone_pattern = r'^(\+880|880|0)?[1-9]\d{8,10}$'
            
            if not re.match(bd_phone_pattern, clean_phone):
                raise ValidationError(
                    'Please enter a valid Bangladesh phone number. '
                    'Format: +880 1XXX-XXXXXX or 01XXX-XXXXXX'
                )
        
        return phone

    def clean_email_primary(self):
        """Validate primary email if provided."""
        email = self.cleaned_data.get('email_primary', '').strip().lower()
        
        if email:  # Optional field
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise ValidationError('Please enter a valid email address.')
        
        return email

    def clean_email_secondary(self):
        """Validate secondary email if provided."""
        email = self.cleaned_data.get('email_secondary', '').strip().lower()
        
        if email:  # Optional field
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise ValidationError('Please enter a valid email address.')
        
        return email

    def clean_website(self):
        """Validate website URL if provided."""
        website = self.cleaned_data.get('website', '').strip()
        
        if website:  # Optional field
            # Add protocol if missing
            if not website.startswith(('http://', 'https://')):
                website = 'https://' + website
            
            # Validate URL format
            from django.core.validators import URLValidator
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            url_validator = URLValidator()
            try:
                url_validator(website)
            except DjangoValidationError:
                raise ValidationError('Please enter a valid website URL.')
        
        return website

    def clean_performance_rating(self):
        """Validate performance rating."""
        rating = self.cleaned_data.get('performance_rating')
        
        if rating is not None:
            if rating < 0 or rating > 5:
                raise ValidationError('Performance rating must be between 0.0 and 5.0.')
        
        return rating

    def clean_postal_code(self):
        """Validate postal code format."""
        postal_code = self.cleaned_data.get('postal_code', '').strip()
        
        if postal_code:  # Optional field
            # Bangladesh postal code validation (4 digits)
            import re
            if not re.match(r'^\d{4}$', postal_code):
                raise ValidationError('Bangladesh postal code should be 4 digits (e.g., 1000).')
        
        return postal_code

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        
        # Get form data
        is_active = cleaned_data.get('is_active', True)
        status = cleaned_data.get('status')
        contact_person = cleaned_data.get('contact_person', '').strip()
        phone_primary = cleaned_data.get('phone_primary', '').strip()
        email_primary = cleaned_data.get('email_primary', '').strip()
        
        # Validate required fields for active vendors
        if is_active and status == 'ACTIVE':
            if not contact_person:
                raise ValidationError({
                    'contact_person': 'Contact person is required for active vendors.'
                })
            
            if not phone_primary:
                raise ValidationError({
                    'phone_primary': 'Primary phone number is required for active vendors.'
                })
        
        # Ensure emails are different if both provided
        email_secondary = cleaned_data.get('email_secondary', '').strip()
        if email_primary and email_secondary and email_primary == email_secondary:
            raise ValidationError({
                'email_secondary': 'Secondary email must be different from primary email.'
            })
        
        # Ensure phone numbers are different if both provided
        phone_secondary = cleaned_data.get('phone_secondary', '').strip()
        if phone_primary and phone_secondary:
            import re
            clean_primary = re.sub(r'[\s\-]', '', phone_primary)
            clean_secondary = re.sub(r'[\s\-]', '', phone_secondary)
            if clean_primary == clean_secondary:
                raise ValidationError({
                    'phone_secondary': 'Secondary phone must be different from primary phone.'
                })
        
        return cleaned_data

    def save(self, commit=True):
        """Override save to handle special formatting."""
        vendor = super().save(commit=False)
        
        # Ensure vendor code is uppercase
        if vendor.vendor_code:
            vendor.vendor_code = vendor.vendor_code.upper().strip()
        
        # Format website URL
        if vendor.website and not vendor.website.startswith(('http://', 'https://')):
            vendor.website = 'https://' + vendor.website
        
        # Set default country if not provided
        if not vendor.country:
            vendor.country = 'Bangladesh'
        
        if commit:
            vendor.save()
        
        return vendor


class VendorSearchForm(forms.Form):
    """
    Form for searching and filtering vendors.
    """
    
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by vendor code, name, contact person, or address...',
            'autocomplete': 'off'
        })
    )
    
    vendor_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Vendor.VENDOR_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Vendor.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by city...'
        })
    )
    
    district = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by district...'
        })
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'All Vendors'),
            ('true', 'Active Only'),
            ('false', 'Inactive Only')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    is_preferred = forms.ChoiceField(
        choices=[
            ('', 'All Vendors'),
            ('true', 'Preferred Only'),
            ('false', 'Non-Preferred Only')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    performance_rating = forms.ChoiceField(
        choices=[
            ('', 'All Ratings'),
            ('5', '5 Stars'),
            ('4', '4+ Stars'),
            ('3', '3+ Stars'),
            ('2', '2+ Stars'),
            ('1', '1+ Stars'),
            ('unrated', 'Unrated')
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
        
        cleaned_data = self.cleaned_data
        
        # Search filter
        search = cleaned_data.get('search')
        if search:
            queryset = queryset.filter(
                Q(vendor_code__icontains=search) |
                Q(name__icontains=search) |
                Q(trade_name__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(address__icontains=search) |
                Q(specialization__icontains=search) |
                Q(phone_primary__icontains=search) |
                Q(email_primary__icontains=search)
            )
        
        # Vendor type filter
        vendor_type = cleaned_data.get('vendor_type')
        if vendor_type:
            queryset = queryset.filter(vendor_type=vendor_type)
        
        # Status filter
        status = cleaned_data.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # City filter
        city = cleaned_data.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # District filter
        district = cleaned_data.get('district')
        if district:
            queryset = queryset.filter(district__icontains=district)
        
        # Active status filter
        is_active = cleaned_data.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)
        
        # Preferred status filter
        is_preferred = cleaned_data.get('is_preferred')
        if is_preferred == 'true':
            queryset = queryset.filter(is_preferred=True)
        elif is_preferred == 'false':
            queryset = queryset.filter(is_preferred=False)
        
        # Performance rating filter
        performance_rating = cleaned_data.get('performance_rating')
        if performance_rating:
            if performance_rating == 'unrated':
                queryset = queryset.filter(performance_rating__isnull=True)
            else:
                rating = int(performance_rating)
                queryset = queryset.filter(performance_rating__gte=rating)
        
        return queryset


class VendorQuickAddForm(forms.ModelForm):
    """
    Simplified form for quickly adding basic vendor information.
    """
    
    class Meta:
        model = Vendor
        fields = [
            'vendor_code', 'name', 'vendor_type',
            'contact_person', 'phone_primary', 'email_primary'
        ]
        
        widgets = {
            'vendor_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'VND001',
                'style': 'text-transform: uppercase;'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company Name'
            }),
            'vendor_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact Person'
            }),
            'phone_primary': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '01712345678'
            }),
            'email_primary': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@company.com'
            })
        }

    def clean_vendor_code(self):
        """Validate vendor code uniqueness."""
        vendor_code = self.cleaned_data.get('vendor_code')
        if vendor_code:
            vendor_code = vendor_code.upper().strip()
            if Vendor.objects.filter(vendor_code=vendor_code).exists():
                raise ValidationError('Vendor code already exists.')
        return vendor_code

    def save(self, commit=True):
        """Save with default values for required fields."""
        vendor = super().save(commit=False)
        
        # Set default values
        if not vendor.address:
            vendor.address = f"Address for {vendor.name}"
        if not vendor.city:
            vendor.city = 'Dhaka'
        if not vendor.district:
            vendor.district = 'Dhaka'
        if not vendor.country:
            vendor.country = 'Bangladesh'
        
        if commit:
            vendor.save()
        
        return vendor


class VendorContactUpdateForm(forms.ModelForm):
    """
    Form for updating only contact information.
    """
    
    class Meta:
        model = Vendor
        fields = [
            'contact_person', 'contact_designation',
            'phone_primary', 'phone_secondary',
            'email_primary', 'email_secondary'
        ]
        
        widgets = {
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_designation': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_primary': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_secondary': forms.TextInput(attrs={'class': 'form-control'}),
            'email_primary': forms.EmailInput(attrs={'class': 'form-control'}),
            'email_secondary': forms.EmailInput(attrs={'class': 'form-control'})
        }


class VendorPerformanceForm(forms.ModelForm):
    """
    Form for updating vendor performance rating and notes.
    """
    
    class Meta:
        model = Vendor
        fields = ['performance_rating', 'is_preferred', 'notes']
        
        widgets = {
            'performance_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '5',
                'step': '0.01'
            }),
            'is_preferred': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            })
        }

    def clean_performance_rating(self):
        """Validate performance rating."""
        rating = self.cleaned_data.get('performance_rating')
        if rating is not None and (rating < 0 or rating > 5):
            raise ValidationError('Rating must be between 0.00 and 5.00.')
        return rating


class VendorBulkUpdateForm(forms.Form):
    """
    Form for bulk updating vendor status and preferences.
    """
    
    action = forms.ChoiceField(
        choices=[
            ('activate', 'Activate Selected'),
            ('deactivate', 'Deactivate Selected'),
            ('mark_preferred', 'Mark as Preferred'),
            ('unmark_preferred', 'Remove Preferred Status'),
            ('suspend', 'Suspend Selected'),
            ('reactivate', 'Reactivate Suspended')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I confirm this bulk action'
    )
    
    selected_vendors = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    def clean_selected_vendors(self):
        """Validate selected vendor IDs."""
        vendor_ids = self.cleaned_data.get('selected_vendors')
        if vendor_ids:
            try:
                ids = [int(id_str) for id_str in vendor_ids.split(',')]
                if not Vendor.objects.filter(id__in=ids).exists():
                    raise ValidationError('Invalid vendor selection.')
                return ids
            except (ValueError, TypeError):
                raise ValidationError('Invalid vendor selection format.')
        raise ValidationError('No vendors selected.')