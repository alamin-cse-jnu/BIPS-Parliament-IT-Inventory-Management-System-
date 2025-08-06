
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Vendor


class VendorForm(forms.ModelForm):
    """
    Form for creating and editing Vendor records.
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
                'style': 'text-transform: uppercase;'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full company/vendor name',
                'maxlength': 200
            }),
            'trade_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter trade name (if different from company name)',
                'maxlength': 200
            }),
            'vendor_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter primary contact person name',
                'maxlength': 100
            }),
            'contact_designation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact person designation (e.g., Sales Manager)',
                'maxlength': 100
            }),
            'phone_primary': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter primary phone number (e.g., 01712345678)',
                'pattern': r'^(\+880|880|0)?1[3-9]\d{8}$',
                'title': 'Enter valid Bangladeshi mobile number'
            }),
            'phone_secondary': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter secondary phone number (optional)',
                'pattern': r'^(\+880|880|0)?1[3-9]\d{8}$',
                'title': 'Enter valid Bangladeshi mobile number'
            }),
            'email_primary': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter primary email address'
            }),
            'email_secondary': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter secondary email address (optional)'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter complete vendor address',
                'rows': 3
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter city name',
                'value': 'Dhaka'
            }),
            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter district name',
                'value': 'Dhaka'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter country name',
                'value': 'Bangladesh'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter postal/ZIP code (optional)',
                'maxlength': 20
            }),
            'business_registration_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter business registration number (optional)',
                'maxlength': 100
            }),
            'tax_identification_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter TIN number (optional)',
                'maxlength': 100
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter website URL (optional)'
            }),
            'specialization': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe areas of specialization or products/services offered',
                'rows': 4
            }),
            'service_categories': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter service categories (comma-separated, e.g., Hardware Supply, Software Installation, Maintenance)',
                'rows': 3
            }),
            'performance_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter rating (0.00 to 5.00)',
                'min': '0',
                'max': '5',
                'step': '0.01'
            }),
            'is_preferred': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter additional notes about the vendor',
                'rows': 4
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mark required fields
        self.fields['vendor_code'].required = True
        self.fields['name'].required = True
        self.fields['contact_person'].required = True
        self.fields['phone_primary'].required = True
        self.fields['email_primary'].required = True
        self.fields['address'].required = True
        
        # Set default values for Bangladesh location
        if not self.instance.pk:  # Only for new records
            self.fields['city'].initial = 'Dhaka'
            self.fields['district'].initial = 'Dhaka'
            self.fields['country'].initial = 'Bangladesh'

    def clean_vendor_code(self):
        """Validate and format vendor code."""
        vendor_code = self.cleaned_data.get('vendor_code')
        if vendor_code:
            vendor_code = vendor_code.upper().strip()
            
            # Check for uniqueness (excluding current instance if editing)
            existing = Vendor.objects.filter(vendor_code=vendor_code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Vendor code already exists.')
        
        return vendor_code

    def clean_name(self):
        """Validate vendor name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            
            # Check for similar names (case-insensitive)
            existing = Vendor.objects.filter(name__iexact=name)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('A vendor with this name already exists.')
        
        return name

    def clean_email_primary(self):
        """Validate primary email uniqueness."""
        email = self.cleaned_data.get('email_primary')
        if email:
            existing = Vendor.objects.filter(email_primary=email)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('This email address is already registered with another vendor.')
        
        return email

    def clean_phone_primary(self):
        """Validate primary phone number uniqueness."""
        phone = self.cleaned_data.get('phone_primary')
        if phone:
            # Normalize phone number (remove spaces, hyphens)
            phone = phone.replace(' ', '').replace('-', '')
            
            existing = Vendor.objects.filter(phone_primary=phone)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('This phone number is already registered with another vendor.')
        
        return phone

    def clean_performance_rating(self):
        """Validate performance rating range."""
        rating = self.cleaned_data.get('performance_rating')
        if rating is not None:
            if rating < 0 or rating > 5:
                raise ValidationError('Performance rating must be between 0.00 and 5.00.')
        
        return rating

    def clean(self):
        """Perform additional cross-field validation."""
        cleaned_data = super().clean()
        
        # Validate status logic
        status = cleaned_data.get('status')
        is_active = cleaned_data.get('is_active')
        
        if status == 'BLACKLISTED' and is_active:
            raise ValidationError({
                'is_active': 'Blacklisted vendors cannot be active.'
            })
        
        # Ensure contact information is provided for active vendors
        if is_active and status == 'ACTIVE':
            contact_person = cleaned_data.get('contact_person', '').strip()
            phone_primary = cleaned_data.get('phone_primary', '').strip()
            
            if not contact_person:
                raise ValidationError({
                    'contact_person': 'Contact person is required for active vendors.'
                })
            
            if not phone_primary:
                raise ValidationError({
                    'phone_primary': 'Primary phone number is required for active vendors.'
                })
        
        return cleaned_data


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