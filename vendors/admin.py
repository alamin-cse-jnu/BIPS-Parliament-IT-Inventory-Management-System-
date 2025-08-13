
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import models
from django.forms import Textarea
from django.http import HttpResponse
from django.utils import timezone
import csv
from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """
    Custom admin interface for Vendor model.
    Provides comprehensive vendor management for Bangladesh Parliament Secretariat.
    """
    
    # Display configuration
    list_display = (
        'vendor_code',
        'name',
        'get_vendor_type_display',
        'get_status_display',
        'contact_person',
        'phone_primary',
        'city',
        'get_performance_display',
        'is_preferred',
        'is_active',
        'created_at'
    )
    
    list_filter = (
        'vendor_type',
        'status',
        'is_active',
        'is_preferred',
        'city',
        'district',
        'country',
        'created_at',
        'performance_rating'
    )
    
    search_fields = (
        'vendor_code',
        'name',
        'trade_name',
        'contact_person',
        'phone_primary',
        'email_primary',
        'address',
        'specialization',
        'business_registration_no',
        'tax_identification_no'
    )
    
    ordering = ('vendor_code', 'name')
    
    # Advanced filtering
    list_per_page = 25
    list_max_show_all = 100
    
    # Form layout configuration
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'vendor_code',
                'name',
                'trade_name',
                'vendor_type',
                'status'
            )
        }),
        ('Contact Information', {
            'fields': (
                'contact_person',
                'contact_designation',
                ('phone_primary', 'phone_secondary'),
                ('email_primary', 'email_secondary')
            )
        }),
        ('Address Information', {
            'fields': (
                'address',
                ('city', 'district'),
                ('country', 'postal_code')
            )
        }),
        ('Business Information', {
            'fields': (
                'business_registration_no',
                'tax_identification_no',
                'website'
            ),
            'classes': ('collapse',)
        }),
        ('Services & Specialization', {
            'fields': (
                'specialization',
                'service_categories'
            ),
            'classes': ('collapse',)
        }),
        ('Performance & Preferences', {
            'fields': (
                'performance_rating',
                'is_preferred',
                'is_active'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': (
                ('created_by', 'updated_by'),
                ('created_at', 'updated_at')
            ),
            'classes': ('collapse',)
        })
    )
    
    # Readonly fields
    readonly_fields = (
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    )
    
    # Form widget customizations
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
    }
    
    # Actions
    actions = [
        'make_active',
        'make_inactive',
        'mark_as_preferred',
        'unmark_as_preferred',
        'export_vendors_csv',
        'export_contact_list',
        'reset_performance_rating'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance."""
        return super().get_queryset(request).select_related(
            'created_by',
            'updated_by'
        )
    
    def save_model(self, request, obj, form, change):
        """Override save to track user who created/updated the vendor."""
        if not change:  # Creating new vendor
            obj.created_by = request.user
        else:  # Updating existing vendor
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    # Custom display methods
    def get_vendor_type_display(self, obj):
        """Display vendor type with icon."""
        icon_class = obj.get_vendor_type_display_icon()
        return format_html(
            '<i class="{}" style="margin-right: 5px;"></i> {}',
            icon_class,
            obj.get_vendor_type_display()
        )
    get_vendor_type_display.short_description = 'Type'
    get_vendor_type_display.admin_order_field = 'vendor_type'
    
    def get_status_display(self, obj):
        """Display status with colored badge."""
        badge_class = obj.get_status_badge_class()
        color_map = {
            'ACTIVE': '#28a745',
            'INACTIVE': '#6c757d',
            'SUSPENDED': '#ffc107',
            'BLACKLISTED': '#dc3545'
        }
        color = color_map.get(obj.status, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_display.short_description = 'Status'
    get_status_display.admin_order_field = 'status'
    
    def get_performance_display(self, obj):
        """Display performance rating with stars."""
        if obj.performance_rating:
            rating = float(obj.performance_rating)
            full_stars = int(rating)
            half_star = rating - full_stars >= 0.5
            empty_stars = 5 - full_stars - (1 if half_star else 0)
            
            stars = '★' * full_stars
            if half_star:
                stars += '☆'
            stars += '☆' * empty_stars
            
            return format_html(
                '<span title="{}/5.00" style="color: #ffc107;">{}</span>',
                rating,
                stars
            )
        return format_html('<span style="color: #ccc;">Not Rated</span>')
    get_performance_display.short_description = 'Rating'
    get_performance_display.admin_order_field = 'performance_rating'
    
    # Bulk Actions
    def make_active(self, request, queryset):
        """Bulk action to activate selected vendors."""
        updated = queryset.update(is_active=True, status='ACTIVE')
        self.message_user(
            request,
            f'{updated} vendor(s) were successfully activated.'
        )
    make_active.short_description = "Activate selected vendors"
    
    def make_inactive(self, request, queryset):
        """Bulk action to deactivate selected vendors."""
        updated = queryset.update(is_active=False, status='INACTIVE')
        self.message_user(
            request,
            f'{updated} vendor(s) were successfully deactivated.'
        )
    make_inactive.short_description = "Deactivate selected vendors"
    
    def mark_as_preferred(self, request, queryset):
        """Bulk action to mark vendors as preferred."""
        updated = queryset.update(is_preferred=True)
        self.message_user(
            request,
            f'{updated} vendor(s) were marked as preferred.'
        )
    mark_as_preferred.short_description = "Mark as preferred vendors"
    
    def unmark_as_preferred(self, request, queryset):
        """Bulk action to unmark vendors as preferred."""
        updated = queryset.update(is_preferred=False)
        self.message_user(
            request,
            f'{updated} vendor(s) were unmarked as preferred.'
        )
    unmark_as_preferred.short_description = "Remove preferred status"
    
    def reset_performance_rating(self, request, queryset):
        """Bulk action to reset performance ratings."""
        updated = queryset.update(performance_rating=None)
        self.message_user(
            request,
            f'Performance ratings reset for {updated} vendor(s).'
        )
    reset_performance_rating.short_description = "Reset performance ratings"
    
    def export_vendors_csv(self, request, queryset):
        """Export selected vendors to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="vendors_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Vendor Code',
            'Name',
            'Trade Name',
            'Type',
            'Status',
            'Contact Person',
            'Designation',
            'Phone Primary',
            'Phone Secondary',
            'Email Primary',
            'Email Secondary',
            'Address',
            'City',
            'District',
            'Country',
            'Postal Code',
            'Business Registration',
            'TIN',
            'Website',
            'Specialization',
            'Performance Rating',
            'Is Preferred',
            'Is Active',
            'Created At'
        ])
        
        # Write vendor data
        for vendor in queryset:
            writer.writerow([
                vendor.vendor_code,
                vendor.name,
                vendor.trade_name,
                vendor.get_vendor_type_display(),
                vendor.get_status_display(),
                vendor.contact_person,
                vendor.contact_designation,
                vendor.phone_primary,
                vendor.phone_secondary,
                vendor.email_primary,
                vendor.email_secondary,
                vendor.address,
                vendor.city,
                vendor.district,
                vendor.country,
                vendor.postal_code,
                vendor.business_registration_no,
                vendor.tax_identification_no,
                vendor.website,
                vendor.specialization,
                vendor.performance_rating,
                'Yes' if vendor.is_preferred else 'No',
                'Yes' if vendor.is_active else 'No',
                vendor.created_at.strftime('%Y-%m-%d %H:%M:%S') if vendor.created_at else ''
            ])
        
        self.message_user(
            request,
            f'Successfully exported {queryset.count()} vendor(s) to CSV.'
        )
        
        return response
    export_vendors_csv.short_description = "Export selected vendors to CSV"
    
    def export_contact_list(self, request, queryset):
        """Export contact information only."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="vendor_contacts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Vendor Code',
            'Company Name',
            'Contact Person',
            'Designation',
            'Phone',
            'Email',
            'Address'
        ])
        
        # Write contact data
        for vendor in queryset.filter(is_active=True):
            writer.writerow([
                vendor.vendor_code,
                vendor.name,
                vendor.contact_person,
                vendor.contact_designation,
                vendor.phone_primary,
                vendor.email_primary,
                vendor.full_address
            ])
        
        self.message_user(
            request,
            f'Successfully exported contact list for {queryset.filter(is_active=True).count()} active vendor(s).'
        )
        
        return response
    export_contact_list.short_description = "Export contact information only"
    
    # Custom filters
    def get_list_filter(self, request):
        """Customize list filters based on user permissions."""
        filters = list(self.list_filter)
        
        # Add performance rating filter only if there are vendors with ratings
        if Vendor.objects.filter(performance_rating__isnull=False).exists():
            if 'performance_rating' not in filters:
                filters.append('performance_rating')
        
        return filters
    
    # Custom views and methods
    def changelist_view(self, request, extra_context=None):
        """Add extra context to the changelist view."""
        extra_context = extra_context or {}
        
        # Add summary statistics
        extra_context['vendor_stats'] = {
            'total': Vendor.objects.count(),
            'active': Vendor.objects.filter(is_active=True).count(),
            'preferred': Vendor.objects.filter(is_preferred=True).count(),
            'suppliers': Vendor.objects.filter(vendor_type='SUPPLIER').count(),
            'service_providers': Vendor.objects.filter(
                vendor_type__in=['MAINTENANCE', 'SUPPORT', 'INSTALLATION']
            ).count()
        }
        
        return super().changelist_view(request, extra_context=extra_context)
    
    class Meta:
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"


# Inline admin classes for use in other models
class VendorInline(admin.TabularInline):
    """
    Inline admin for vendors - can be used in device or maintenance models.
    """
    model = Vendor
    extra = 0
    fields = ['vendor_code', 'name', 'contact_person', 'phone_primary', 'is_active']
    readonly_fields = ['vendor_code']
    
    def get_queryset(self, request):
        """Show only active vendors in inline."""
        return super().get_queryset(request).filter(is_active=True)


# Custom admin site configuration enhancements
def customize_admin_site():
    """Customize the admin site for PIMS."""
    admin.site.site_header = "PIMS - Bangladesh Parliament Secretariat"
    admin.site.site_title = "PIMS Vendor Management"
    admin.site.index_title = "Vendor Management System"
    
    # Add custom CSS if needed
    admin.site.enable_nav_sidebar = True


# Call the customization
customize_admin_site()