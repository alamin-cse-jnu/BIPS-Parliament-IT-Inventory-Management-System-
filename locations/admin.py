from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Building, Floor, Block, Room, Office, Location, LocationQRCode


# ============================================================================
# QR CODE INLINE AND ADMIN CLASSES
# ============================================================================

class LocationQRCodeInline(admin.TabularInline):
    """Inline admin for Location QR codes."""
    model = LocationQRCode
    extra = 0
    fields = ('qr_code_preview', 'qr_data', 'is_active', 'created_at')
    readonly_fields = ('qr_code_preview', 'qr_data', 'created_at')
    
    def qr_code_preview(self, obj):
        """Display QR code image preview."""
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="50" height="50" />',
                obj.qr_code.url
            )
        return "No QR Code"
    qr_code_preview.short_description = "QR Code"


@admin.register(LocationQRCode)
class LocationQRCodeAdmin(admin.ModelAdmin):
    """Admin interface for Location QR Codes."""
    
    list_display = (
        'location',
        'qr_code_preview',
        'is_active',
        'size',
        'format',
        'created_at'
    )
    list_filter = ('is_active', 'format', 'size', 'created_at')
    search_fields = (
        'location__name', 
        'location__location_code',
        'location__building__name'
    )
    readonly_fields = ('qr_code_id', 'qr_code_preview', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Location Information', {
            'fields': ('location',)
        }),
        ('QR Code Details', {
            'fields': ('qr_code_id', 'qr_code', 'qr_code_preview', 'qr_data')
        }),
        ('Settings', {
            'fields': ('size', 'format', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def qr_code_preview(self, obj):
        """Display QR code image preview in admin."""
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="100" height="100" style="border: 1px solid #ddd;" />',
                obj.qr_code.url
            )
        return "No QR Code"
    qr_code_preview.short_description = "QR Code Preview"


# ============================================================================
#  ADMIN CLASSES 
# ============================================================================

@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    """
    Admin configuration for Building model.
    """
    list_display = ['code', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['code', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        """Optimize queryset for list display."""
        return super().get_queryset(request).select_related()

    class Meta:
        verbose_name = "Building"
        verbose_name_plural = "Buildings"


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    """
    Admin configuration for Floor model.
    """
    list_display = ['name', 'floor_number', 'is_active', 'created_at']
    list_filter = ['is_active', 'floor_number', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['floor_number', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'floor_number', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset for list display."""
        return super().get_queryset(request).select_related()

    class Meta:
        verbose_name = "Floor"
        verbose_name_plural = "Floors"


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    """
    Admin configuration for Block model.
    """
    list_display = ['code', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['code', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset for list display."""
        return super().get_queryset(request).select_related()

    class Meta:
        verbose_name = "Block"
        verbose_name_plural = "Blocks"


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """
    Admin configuration for Room model.
    """
    list_display = ['room_number', 'name', 'room_type', 'capacity', 'area_sqft', 'is_active']
    list_filter = ['room_type', 'is_active', 'created_at']
    search_fields = ['name', 'room_number', 'description']
    ordering = ['room_number', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'room_number', 'room_type')
        }),
        ('Physical Details', {
            'fields': ('capacity', 'area_sqft', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset for list display."""
        return super().get_queryset(request).select_related()

    class Meta:
        verbose_name = "Room"
        verbose_name_plural = "Rooms"


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    """
    Admin configuration for Office model.
    """
    list_display = ['office_code', 'name', 'office_type', 'head_of_office', 'contact_number', 'is_active']
    list_filter = ['office_type', 'is_active', 'created_at']
    search_fields = ['name', 'office_code', 'head_of_office', 'email', 'description']
    ordering = ['office_code', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'office_code', 'office_type')
        }),
        ('Administrative Details', {
            'fields': ('head_of_office', 'contact_number', 'email', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset for list display."""
        return super().get_queryset(request).select_related()

    class Meta:
        verbose_name = "Office"
        verbose_name_plural = "Offices"


# ============================================================================
# LOCATION ADMIN WITH QR CODE INTEGRATION
# ============================================================================

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Location model with comprehensive display and QR code management.
    """
    list_display = [
        'location_code', 
        'name', 
        'get_building_info',
        'get_floor_info',
        'get_block_info', 
        'get_room_info',
        'get_office_info',
        'has_coordinates_display',
        'has_qr_code_display',  # NEW: QR code status
        'is_active'
    ]
    
    list_filter = [
        'is_active', 
        'building', 
        'floor', 
        'office__office_type',
        'room__room_type',
        'created_at'
    ]
    
    search_fields = [
        'name', 
        'location_code', 
        'address',
        'building__name',
        'floor__name',
        'block__name',
        'room__name',
        'office__name',
        'notes'
    ]
    
    ordering = ['location_code', 'name']
    
    fieldsets = (
        ('Location Identification', {
            'fields': ('name', 'location_code', 'address')
        }),
        ('Location Components', {
            'fields': ('building', 'floor', 'block', 'room', 'office'),
            'description': 'Select at least one location component. These components are independent of each other.'
        }),
        ('Geo-coordinates', {
            'fields': ('latitude', 'longitude'),
            'description': 'Optional geo-coordinates for this location. Both latitude and longitude must be provided together.',
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    # ADD: QR Code inline
    inlines = [LocationQRCodeInline]
    
    # ADD: QR code generation action
    actions = [
        'make_active', 
        'make_inactive', 
        'export_coordinates',
        'generate_qr_codes'  # NEW: QR code generation action
    ]
    
    # Optimize database queries
    def get_queryset(self, request):
        """Optimize queryset with select_related for foreign keys."""
        return super().get_queryset(request).select_related(
            'building', 'floor', 'block', 'room', 'office'
        ).prefetch_related('qr_codes')  # NEW: Prefetch QR codes

    # Custom display methods for list view (existing methods unchanged)
    def get_building_info(self, obj):
        """Display building information in list view."""
        if obj.building:
            return format_html(
                '<span class="badge badge-primary">{}</span>',
                obj.building.code
            )
        return format_html('<span class="text-muted">-</span>')
    get_building_info.short_description = 'Building'
    get_building_info.admin_order_field = 'building__code'

    def get_floor_info(self, obj):
        """Display floor information in list view."""
        if obj.floor:
            return format_html(
                '<span class="badge badge-info">Level {}</span>',
                obj.floor.floor_number
            )
        return format_html('<span class="text-muted">-</span>')
    get_floor_info.short_description = 'Floor'
    get_floor_info.admin_order_field = 'floor__floor_number'

    def get_block_info(self, obj):
        """Display block information in list view."""
        if obj.block:
            return format_html(
                '<span class="badge badge-secondary">{}</span>',
                obj.block.code
            )
        return format_html('<span class="text-muted">-</span>')
    get_block_info.short_description = 'Block'
    get_block_info.admin_order_field = 'block__code'

    def get_room_info(self, obj):
        """Display room information in list view."""
        if obj.room:
            return format_html(
                '<span class="badge badge-success">{}</span>',
                obj.room.room_number
            )
        return format_html('<span class="text-muted">-</span>')
    get_room_info.short_description = 'Room'
    get_room_info.admin_order_field = 'room__room_number'

    def get_office_info(self, obj):
        """Display office information in list view."""
        if obj.office:
            return format_html(
                '<span class="badge badge-warning">{}</span>',
                obj.office.office_code
            )
        return format_html('<span class="text-muted">-</span>')
    get_office_info.short_description = 'Office'
    get_office_info.admin_order_field = 'office__office_code'

    def has_coordinates_display(self, obj):
        """Display coordinate status with icon."""
        if obj.has_coordinates():
            return format_html(
                '<span class="text-success" title="Lat: {}, Lng: {}">✓ GPS</span>',
                obj.latitude,
                obj.longitude
            )
        return format_html('<span class="text-muted">✗ No GPS</span>')
    has_coordinates_display.short_description = 'Coordinates'
    has_coordinates_display.admin_order_field = 'latitude'

    # NEW: QR code status display
    def has_qr_code_display(self, obj):
        """Display QR code status with icon and link."""
        active_qr = obj.qr_codes.filter(is_active=True).first()
        if active_qr:
            download_url = reverse('admin:locations_locationqrcode_change', args=[active_qr.pk])
            return format_html(
                '<a href="{}" title="View QR Code"><span class="text-success">✓ QR Code</span></a>',
                download_url
            )
        return format_html('<span class="text-muted">✗ No QR</span>')
    has_qr_code_display.short_description = 'QR Code'

    # Custom actions (existing actions unchanged)
    def make_active(self, request, queryset):
        """Bulk action to activate selected locations."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} location(s) were successfully marked as active.'
        )
    make_active.short_description = "Mark selected locations as active"

    def make_inactive(self, request, queryset):
        """Bulk action to deactivate selected locations."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} location(s) were successfully marked as inactive.'
        )
    make_inactive.short_description = "Mark selected locations as inactive"

    def export_coordinates(self, request, queryset):
        """Export coordinates of selected locations."""
        locations_with_coords = queryset.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        if not locations_with_coords.exists():
            self.message_user(
                request,
                'No locations with coordinates found in selection.',
                level='warning'
            )
            return
        
        # This could be enhanced to generate a CSV/JSON export
        coord_list = []
        for location in locations_with_coords:
            coord_list.append(
                f"{location.name}: {location.latitude}, {location.longitude}"
            )
        
        self.message_user(
            request,
            f'Coordinates for {len(coord_list)} locations: ' + '; '.join(coord_list)
        )
    export_coordinates.short_description = "Export coordinates for selected locations"

    # NEW: QR code generation action
    def generate_qr_codes(self, request, queryset):
        """Generate QR codes for selected locations."""
        from pims.utils.qr_code import create_location_qr_code
        
        generated_count = 0
        updated_count = 0
        error_count = 0
        
        for location in queryset:
            try:
                # Check if location already has active QR code
                existing_qr = location.qr_codes.filter(is_active=True).first()
                
                # Generate QR code
                qr_code = create_location_qr_code(location, request)
                
                if qr_code:
                    if existing_qr:
                        updated_count += 1
                    else:
                        generated_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                continue
        
        # Prepare success message
        message_parts = []
        if generated_count > 0:
            message_parts.append(f'Generated {generated_count} new QR codes')
        if updated_count > 0:
            message_parts.append(f'Updated {updated_count} existing QR codes')
        if error_count > 0:
            message_parts.append(f'{error_count} errors occurred')
        
        if message_parts:
            if error_count == 0:
                self.message_user(request, '. '.join(message_parts) + '!')
            else:
                self.message_user(request, '. '.join(message_parts) + '.', level='warning')
        else:
            self.message_user(request, 'No QR codes were generated.', level='warning')
    
    generate_qr_codes.short_description = "Generate QR codes for selected locations"

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"


# ============================================================================
# ADDITIONAL ADMIN CONFIGURATIONS
# ============================================================================

class LocationInline(admin.TabularInline):
    """
    Inline admin for locations - can be used in other models if needed.
    """
    model = Location
    extra = 0
    fields = ['location_code', 'name', 'latitude', 'longitude', 'is_active']
    readonly_fields = ['location_code']


# Custom admin site configuration (optional)
admin.site.site_header = "PIMS - Parliament IT Inventory Management"
admin.site.site_title = "PIMS Admin"
admin.site.index_title = "Welcome to PIMS Administration"