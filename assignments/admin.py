# assignments/admin.py
"""
Django Admin for Assignments - Bangladesh Parliament Secretariat PIMS
Simple and efficient assignment interface for existing devices, employees, and locations.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.db import models
import csv
from datetime import date

from .models import Assignment, AssignmentQRCode


class AssignmentQRCodeInline(admin.TabularInline):
    """QR Code inline for assignments."""
    model = AssignmentQRCode
    extra = 0
    readonly_fields = ('qr_code_id', 'qr_preview', 'created_at')
    fields = ('qr_code_id', 'qr_preview', 'is_active', 'created_at')
    
    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="40" height="40">', obj.qr_code.url)
        return "No QR"
    qr_preview.short_description = "QR Code"
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """
    Simple Assignment Admin - Easy assignment and updates
    """
    
    list_display = [
        'assignment_id',
        'device_info',
        'employee_info',
        'location_info',
        'status_display',
        'assigned_date',
        'qr_status'
    ]
    
    list_filter = [
        'status',
        'assignment_type',
        'assigned_date',
        'is_active'
    ]
    
    search_fields = [
        'assignment_id',
        'device__device_id',
        'device__name',
        'assigned_to__first_name',
        'assigned_to__last_name',
        'assigned_to__username'
    ]
    
    fieldsets = (
        ('🎯 Assignment Setup', {
            'fields': (
                ('device', 'assigned_to'),
                ('assigned_location', 'assignment_type'),
                ('assigned_date', 'expected_return_date'),
                'purpose'
            )
        }),
        ('📋 Status & Returns', {
            'fields': (
                ('status', 'actual_return_date'),
                'notes'
            ),
            'classes': ('collapse',)
        }),
        ('ℹ️ System Info', {
            'fields': ('assignment_id', 'created_at', 'is_active'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [AssignmentQRCodeInline]
    readonly_fields = ['assignment_id', 'created_at']
    list_per_page = 20
    ordering = ['-assigned_date']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize dropdowns for easy selection."""
        
        if db_field.name == "device":
            # Show available devices + current device (for updates)
            assignment_id = request.resolver_match.kwargs.get('object_id')
            if assignment_id:  # Editing existing assignment
                try:
                    current = Assignment.objects.get(pk=assignment_id)
                    kwargs["queryset"] = db_field.related_model.objects.filter(
                        models.Q(status='AVAILABLE', is_active=True) |
                        models.Q(pk=current.device.pk if current.device else None)
                    ).order_by('device_id')
                except:
                    kwargs["queryset"] = db_field.related_model.objects.filter(
                        status='AVAILABLE', is_active=True
                    ).order_by('device_id')
            else:  # New assignment
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    status='AVAILABLE', is_active=True
                ).order_by('device_id')
            kwargs["empty_label"] = "Select Available Device..."
            
        elif db_field.name == "assigned_to":
            kwargs["queryset"] = db_field.related_model.objects.filter(
                is_active=True
            ).order_by('first_name', 'last_name')
            kwargs["empty_label"] = "Select Employee..."
            
        elif db_field.name == "assigned_location":
            kwargs["queryset"] = db_field.related_model.objects.filter(
                is_active=True
            ).order_by('name')
            kwargs["empty_label"] = "Select Location (Optional)..."
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_form(self, request, obj=None, **kwargs):
        """Set defaults and help texts."""
        form = super().get_form(request, obj, **kwargs)
        
        if not obj:  # New assignment
            form.base_fields['assignment_type'].initial = 'TEMPORARY'
            form.base_fields['status'].initial = 'ASSIGNED'
            form.base_fields['assigned_date'].initial = date.today()
        
        # Help texts
        form.base_fields['device'].help_text = "Device to assign"
        form.base_fields['assigned_to'].help_text = "Parliament employee"
        form.base_fields['assigned_location'].help_text = "Where device will be used"
        form.base_fields['purpose'].help_text = "Reason for assignment"
        
        return form
    
    def save_model(self, request, obj, form, change):
        """Handle assignment creation and updates."""
        
        # For updates, get original values
        original_device = None
        original_status = None
        if change:
            try:
                original = Assignment.objects.get(pk=obj.pk)
                original_device = original.device
                original_status = original.status
            except:
                pass
        
        super().save_model(request, obj, form, change)
        
        if not change:  # NEW ASSIGNMENT
            # Update device status
            if obj.device and obj.status == 'ASSIGNED':
                obj.device.status = 'ASSIGNED'
                obj.device.save()
            
            # Generate QR code
            try:
                from pims.utils.qr_code import create_assignment_qr_code
                create_assignment_qr_code(obj, request)
                messages.success(request, f'Assignment {obj.assignment_id} created! QR code ready for printing.')
            except Exception as e:
                messages.warning(request, f'Assignment created but QR failed: {str(e)}')
                
        else:  # ASSIGNMENT UPDATE
            device_changed = original_device != obj.device
            status_changed = original_status != obj.status
            
            # Handle device changes
            if device_changed:
                # Release old device
                if original_device and original_status == 'ASSIGNED':
                    original_device.status = 'AVAILABLE'
                    original_device.save()
                
                # Assign new device
                if obj.device and obj.status == 'ASSIGNED':
                    obj.device.status = 'ASSIGNED'
                    obj.device.save()
                
                # Generate new QR code
                try:
                    from pims.utils.qr_code import create_assignment_qr_code
                    create_assignment_qr_code(obj, request)
                    messages.success(request, f'Device changed! New QR code generated.')
                except:
                    messages.warning(request, 'Device changed but QR generation failed.')
            
            # Handle status changes
            elif status_changed:
                if obj.status == 'RETURNED' and obj.device:
                    obj.device.status = 'AVAILABLE'
                    obj.device.save()
                    messages.success(request, f'Assignment returned. Device is now available.')
                elif obj.status == 'ASSIGNED' and obj.device:
                    obj.device.status = 'ASSIGNED'
                    obj.device.save()
                    messages.success(request, f'Assignment reactivated.')
            
            # General update
            if not device_changed and not status_changed:
                messages.success(request, f'Assignment {obj.assignment_id} updated.')
    
    # Display methods
    def device_info(self, obj):
        if obj.device:
            return format_html('<strong>{}</strong><br><small>{}</small>', 
                             obj.device.device_id, obj.device.name[:30])
        return "No Device"
    device_info.short_description = "Device"
    
    def employee_info(self, obj):
        if obj.assigned_to:
            return format_html('<strong>{}</strong><br><small>{}</small>',
                             obj.assigned_to.get_full_name(), obj.assigned_to.username)
        return "No Employee"
    employee_info.short_description = "Employee"
    
    def location_info(self, obj):
        return obj.assigned_location.name if obj.assigned_location else "No Location"
    location_info.short_description = "Location"
    
    def status_display(self, obj):
        colors = {
            'ASSIGNED': '#28a745',
            'RETURNED': '#6c757d',
            'OVERDUE': '#dc3545',
            'LOST': '#fd7e14',
            'DAMAGED': '#e83e8c'
        }
        color = colors.get(obj.status, '#007bff')
        
        extra = ""
        if obj.status == 'ASSIGNED' and obj.is_overdue():
            extra = " ⚠️"
            color = '#dc3545'
        
        return format_html('<span style="color: {}; font-weight: bold;">{}{}</span>',
                         color, obj.get_status_display(), extra)
    status_display.short_description = "Status"
    
    def qr_status(self, obj):
        qr_exists = obj.qr_codes.filter(is_active=True).exists()
        if qr_exists:
            return format_html('<span style="color: #28a745;">✓ Ready</span>')
        return format_html('<span style="color: #dc3545;">✗ Missing</span>')
    qr_status.short_description = "QR Code"
    
    # Admin actions
    actions = ['mark_returned', 'generate_qr_codes', 'export_csv']
    
    def mark_returned(self, request, queryset):
        """Mark assignments as returned."""
        count = 0
        for assignment in queryset.filter(status='ASSIGNED'):
            assignment.status = 'RETURNED'
            assignment.actual_return_date = date.today()
            assignment.save()
            
            # Make device available
            if assignment.device:
                assignment.device.status = 'AVAILABLE'
                assignment.device.save()
            count += 1
        
        messages.success(request, f'{count} assignments returned. Devices are now available.')
    mark_returned.short_description = "Mark as returned"
    
    def generate_qr_codes(self, request, queryset):
        """Generate QR codes for assignments."""
        from pims.utils.qr_code import create_assignment_qr_code
        count = 0
        for assignment in queryset:
            if not assignment.qr_codes.filter(is_active=True).exists():
                try:
                    create_assignment_qr_code(assignment, request)
                    count += 1
                except:
                    pass
        
        messages.success(request, f'{count} QR codes generated.')
    generate_qr_codes.short_description = "Generate QR codes"
    
    def export_csv(self, request, queryset):
        """Export assignments to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="assignments_{date.today()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Assignment ID', 'Device ID', 'Employee', 'Location', 'Status', 'Assigned Date'])
        
        for assignment in queryset:
            writer.writerow([
                assignment.assignment_id,
                assignment.device.device_id if assignment.device else '',
                assignment.assigned_to.get_full_name() if assignment.assigned_to else '',
                assignment.assigned_location.name if assignment.assigned_location else '',
                assignment.get_status_display(),
                assignment.assigned_date
            ])
        
        return response
    export_csv.short_description = "Export to CSV"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'device', 'assigned_to', 'assigned_location'
        ).prefetch_related('qr_codes')


@admin.register(AssignmentQRCode)
class AssignmentQRCodeAdmin(admin.ModelAdmin):
    """Simple QR Code admin."""
    
    list_display = ['qr_code_id', 'assignment_info', 'qr_preview', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['assignment__assignment_id', 'assignment__device__device_id']
    readonly_fields = ['qr_code_id', 'qr_data', 'created_at', 'updated_at', 'qr_large']
    
    fieldsets = (
        ('QR Code', {
            'fields': ('assignment', 'qr_code_id', 'qr_code', 'qr_large')
        }),
        ('Settings', {
            'fields': ('is_active', 'size', 'format'),
            'classes': ('collapse',)
        })
    )
    
    def assignment_info(self, obj):
        if obj.assignment:
            return format_html('<strong>{}</strong><br>{}',
                             obj.assignment.assignment_id,
                             obj.assignment.device.device_id if obj.assignment.device else 'No Device')
        return "No Assignment"
    assignment_info.short_description = "Assignment"
    
    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="40" height="40">', obj.qr_code.url)
        return "No QR"
    qr_preview.short_description = "Preview"
    
    def qr_large(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="150" height="150">', obj.qr_code.url)
        return "No QR Code"
    qr_large.short_description = "QR Code"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('assignment', 'assignment__device')