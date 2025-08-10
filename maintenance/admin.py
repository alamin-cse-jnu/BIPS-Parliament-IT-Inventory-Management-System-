"""
Django Admin configuration for Maintenance app in PIMS
Bangladesh Parliament Secretariat

This module customizes the Django admin interface for Maintenance model
and provides comprehensive maintenance management capabilities with
enhanced filtering, actions, and reporting features.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.db import models
from django.forms import Textarea
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Count, Sum, Avg, Q
from django.template.response import TemplateResponse
from decimal import Decimal
import csv
from datetime import datetime, timedelta

from .models import Maintenance


class MaintenanceAdminForm(admin.ModelForm):
    """
    Custom form for Maintenance admin with enhanced validation.
    """
    class Meta:
        model = Maintenance
        fields = '__all__'
        widgets = {
            'description': Textarea(attrs={'rows': 3, 'cols': 80}),
            'problem_reported': Textarea(attrs={'rows': 3, 'cols': 80}),
            'work_performed': Textarea(attrs={'rows': 4, 'cols': 80}),
            'parts_replaced': Textarea(attrs={'rows': 3, 'cols': 80}),
            'result_notes': Textarea(attrs={'rows': 3, 'cols': 80}),
            'internal_notes': Textarea(attrs={'rows': 3, 'cols': 80}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields required based on status
        if self.instance and self.instance.status == 'COMPLETED':
            self.fields['work_performed'].required = True
            self.fields['result'].required = True
            self.fields['actual_cost'].required = True
        
        # Customize field help texts
        self.fields['device'].help_text = "Select the device requiring maintenance"
        self.fields['vendor'].help_text = "Select external vendor (if applicable)"
        self.fields['estimated_cost'].help_text = "Estimated cost in BDT"
        self.fields['actual_cost'].help_text = "Final cost in BDT (required when completed)"
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        start_date = cleaned_data.get('start_date')
        expected_end_date = cleaned_data.get('expected_end_date')
        
        # Custom validation based on status
        if status == 'COMPLETED':
            if not cleaned_data.get('work_performed'):
                self.add_error('work_performed', 'Work performed description is required for completed maintenance.')
            if not cleaned_data.get('result'):
                self.add_error('result', 'Maintenance result is required for completed maintenance.')
        
        # Date validation
        if start_date and expected_end_date and start_date >= expected_end_date:
            self.add_error('expected_end_date', 'End date must be after start date.')
        
        return cleaned_data


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    """
    Comprehensive admin interface for Maintenance model.
    Provides advanced maintenance management for Bangladesh Parliament Secretariat.
    """
    
    form = MaintenanceAdminForm
    
    # Display configuration
    list_display = (
        'maintenance_id',
        'get_device_info',
        'get_maintenance_type_badge',
        'get_priority_badge',
        'get_status_badge',
        'start_date',
        'expected_end_date',
        'get_progress_display',
        'get_cost_display',
        'get_vendor_info',
        'get_overdue_display',
        'created_at'
    )
    
    list_filter = (
        'status',
        'maintenance_type',
        'priority',
        'provider_type',
        'result',
        'is_active',
        'requires_approval',
        'is_warranty_service',
        ('start_date', admin.DateFieldListFilter),
        ('expected_end_date', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        'device__subcategory__category',
        'vendor',
        'created_by'
    )
    
    search_fields = (
        'maintenance_id',
        'title',
        'description',
        'device__device_id',
        'device__brand',
        'device__model',
        'vendor__name',
        'technician_name',
        'problem_reported',
        'work_performed'
    )
    
    ordering = ('-start_date', '-created_at')
    
    # Advanced options
    list_per_page = 25
    list_max_show_all = 100
    save_on_top = True
    
    # Form layout configuration
    fieldsets = (
        ('Maintenance Identification', {
            'fields': (
                'maintenance_id',
                'device',
                'title'
            )
        }),
        ('Maintenance Details', {
            'fields': (
                'maintenance_type',
                'priority',
                'status',
                'description',
                'problem_reported'
            )
        }),
        ('Scheduling', {
            'fields': (
                ('start_date', 'expected_end_date'),
                ('actual_start_date', 'actual_end_date'),
                ('follow_up_required', 'follow_up_date'),
                'next_maintenance_due'
            ),
            'classes': ('wide',)
        }),
        ('Service Provider', {
            'fields': (
                'provider_type',
                'vendor',
                ('technician_name', 'technician_contact')
            ),
            'classes': ('collapse',)
        }),
        ('Cost Information', {
            'fields': (
                ('estimated_cost', 'actual_cost'),
                ('parts_cost', 'labor_cost'),
                'is_warranty_service'
            ),
            'classes': ('collapse',)
        }),
        ('Work Details', {
            'fields': (
                'work_performed',
                'parts_replaced',
                ('result', 'result_notes'),
                ('satisfaction_rating', 'downtime_hours')
            ),
            'classes': ('collapse',)
        }),
        ('Approval & Authorization', {
            'fields': (
                'requires_approval',
                ('approved_by', 'approved_at')
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': (
                'is_active',
                'internal_notes',
                ('created_by', 'updated_by')
            ),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': (
                'uuid',
                ('created_at', 'updated_at')
            ),
            'classes': ('collapse',)
        })
    )
    
    # Read-only fields
    readonly_fields = (
        'maintenance_id',
        'uuid',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    )
    
    # Raw ID fields for performance
    raw_id_fields = ('device', 'vendor', 'approved_by')
    
    # Actions
    actions = [
        'mark_as_in_progress',
        'mark_as_completed',
        'mark_as_cancelled',
        'approve_maintenance',
        'export_to_csv',
        'generate_maintenance_report',
        'schedule_follow_up'
    ]
    
    # Custom display methods
    def get_device_info(self, obj):
        """Display device information with link."""
        if obj.device:
            device_url = reverse('admin:devices_device_change', args=[obj.device.pk])
            return format_html(
                '<a href="{}" target="_blank" title="View Device Details">'
                '<strong>{}</strong><br>'
                '<small style="color: #666;">{} {}</small>'
                '</a>',
                device_url,
                obj.device.device_id,
                obj.device.brand,
                obj.device.model
            )
        return '-'
    get_device_info.short_description = 'Device'
    get_device_info.admin_order_field = 'device__device_id'
    
    def get_maintenance_type_badge(self, obj):
        """Display maintenance type as colored badge."""
        type_colors = {
            'PREVENTIVE': '#28a745',    # Green
            'CORRECTIVE': '#ffc107',    # Yellow
            'EMERGENCY': '#dc3545',     # Red
            'UPGRADE': '#007bff',       # Blue
            'INSPECTION': '#17a2b8',    # Cyan
            'CLEANING': '#6f42c1',      # Purple
            'CALIBRATION': '#fd7e14',   # Orange
            'REPLACEMENT': '#e83e8c',   # Pink
            'WARRANTY': '#20c997',      # Teal
            'OTHER': '#6c757d',         # Gray
        }
        color = type_colors.get(obj.maintenance_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_maintenance_type_display()
        )
    get_maintenance_type_badge.short_description = 'Type'
    get_maintenance_type_badge.admin_order_field = 'maintenance_type'
    
    def get_priority_badge(self, obj):
        """Display priority as colored badge."""
        priority_colors = {
            'LOW': '#28a745',       # Green
            'MEDIUM': '#ffc107',    # Yellow
            'HIGH': '#fd7e14',      # Orange
            'CRITICAL': '#dc3545',  # Red
            'EMERGENCY': '#6f42c1', # Purple
        }
        color = priority_colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_priority_display()
        )
    get_priority_badge.short_description = 'Priority'
    get_priority_badge.admin_order_field = 'priority'
    
    def get_status_badge(self, obj):
        """Display status as colored badge."""
        status_colors = {
            'SCHEDULED': '#17a2b8',   # Cyan
            'IN_PROGRESS': '#ffc107', # Yellow
            'ON_HOLD': '#6c757d',     # Gray
            'COMPLETED': '#28a745',   # Green
            'CANCELLED': '#343a40',   # Dark
            'FAILED': '#dc3545',      # Red
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'
    
    def get_progress_display(self, obj):
        """Display maintenance progress."""
        if obj.status == 'COMPLETED':
            return format_html(
                '<div style="width: 100px; background-color: #e9ecef; border-radius: 10px; height: 20px;">'
                '<div style="width: 100%; background-color: #28a745; height: 20px; border-radius: 10px; '
                'display: flex; align-items: center; justify-content: center; color: white; font-size: 11px;">'
                '100%</div></div>'
            )
        elif obj.status in ['CANCELLED', 'FAILED']:
            return format_html('<span style="color: #dc3545;">●</span> {}', obj.get_status_display())
        else:
            progress = obj.progress_percentage
            color = '#28a745' if progress >= 75 else '#ffc107' if progress >= 50 else '#dc3545'
            return format_html(
                '<div style="width: 100px; background-color: #e9ecef; border-radius: 10px; height: 20px;">'
                '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 10px; '
                'display: flex; align-items: center; justify-content: center; color: white; font-size: 11px;">'
                '{}%</div></div>',
                progress, color, progress
            )
    get_progress_display.short_description = 'Progress'
    
    def get_cost_display(self, obj):
        """Display cost information."""
        if obj.actual_cost:
            variance = obj.cost_variance
            if variance > 0:
                variance_color = '#dc3545'  # Red for over budget
                variance_icon = '↗'
            elif variance < 0:
                variance_color = '#28a745'  # Green for under budget
                variance_icon = '↘'
            else:
                variance_color = '#28a745'
                variance_icon = '='
            
            return format_html(
                '<strong>৳{:,.2f}</strong><br>'
                '<small style="color: {};">{} ৳{:,.2f}</small>',
                obj.actual_cost,
                variance_color,
                variance_icon,
                abs(variance)
            )
        elif obj.estimated_cost:
            return format_html(
                '<span style="color: #6c757d;">Est: ৳{:,.2f}</span>',
                obj.estimated_cost
            )
        return '-'
    get_cost_display.short_description = 'Cost (BDT)'
    get_cost_display.admin_order_field = 'actual_cost'
    
    def get_vendor_info(self, obj):
        """Display vendor information."""
        if obj.vendor:
            vendor_url = reverse('admin:vendors_vendor_change', args=[obj.vendor.pk])
            return format_html(
                '<a href="{}" target="_blank" title="View Vendor Details">'
                '{}</a>',
                vendor_url,
                obj.vendor.name[:20] + ('...' if len(obj.vendor.name) > 20 else '')
            )
        elif obj.provider_type == 'INTERNAL':
            return format_html('<span style="color: #28a745;">Internal IT Team</span>')
        return '-'
    get_vendor_info.short_description = 'Service Provider'
    get_vendor_info.admin_order_field = 'vendor__name'
    
    def get_overdue_display(self, obj):
        """Display overdue status."""
        if obj.is_overdue:
            days_overdue = obj.days_overdue
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;" title="Overdue by {} days">'
                '⚠ {} day{}</span>',
                days_overdue,
                days_overdue,
                's' if days_overdue != 1 else ''
            )
        elif obj.is_due_soon():
            days_until = obj.days_until_due
            return format_html(
                '<span style="color: #ffc107;" title="Due in {} days">'
                '⏰ {} day{}</span>',
                days_until,
                days_until,
                's' if days_until != 1 else ''
            )
        return ''
    get_overdue_display.short_description = 'Due Status'
    
    # Custom actions
    def mark_as_in_progress(self, request, queryset):
        """Mark selected maintenance as in progress."""
        updated = 0
        for maintenance in queryset:
            if maintenance.can_be_started():
                maintenance.status = 'IN_PROGRESS'
                maintenance.actual_start_date = timezone.now()
                maintenance.save()
                updated += 1
        
        self.message_user(
            request,
            f'{updated} maintenance record(s) marked as in progress.',
            messages.SUCCESS
        )
    mark_as_in_progress.short_description = "Mark selected as In Progress"
    
    def mark_as_completed(self, request, queryset):
        """Mark selected maintenance as completed."""
        updated = 0
        for maintenance in queryset:
            if maintenance.can_be_completed():
                maintenance.status = 'COMPLETED'
                maintenance.actual_end_date = timezone.now()
                if not maintenance.result:
                    maintenance.result = 'SUCCESS'
                maintenance.save()
                updated += 1
        
        self.message_user(
            request,
            f'{updated} maintenance record(s) marked as completed.',
            messages.SUCCESS
        )
    mark_as_completed.short_description = "Mark selected as Completed"
    
    def mark_as_cancelled(self, request, queryset):
        """Cancel selected maintenance."""
        updated = 0
        for maintenance in queryset:
            if maintenance.can_be_cancelled():
                maintenance.status = 'CANCELLED'
                maintenance.save()
                updated += 1
        
        self.message_user(
            request,
            f'{updated} maintenance record(s) cancelled.',
            messages.WARNING
        )
    mark_as_cancelled.short_description = "Cancel selected maintenance"
    
    def approve_maintenance(self, request, queryset):
        """Approve selected maintenance requiring approval."""
        if not request.user.has_perm('maintenance.approve_maintenance'):
            self.message_user(
                request,
                'You do not have permission to approve maintenance.',
                messages.ERROR
            )
            return
        
        updated = 0
        for maintenance in queryset.filter(requires_approval=True, approved_by__isnull=True):
            maintenance.approved_by = request.user
            maintenance.approved_at = timezone.now()
            maintenance.save()
            updated += 1
        
        self.message_user(
            request,
            f'{updated} maintenance record(s) approved.',
            messages.SUCCESS
        )
    approve_maintenance.short_description = "Approve selected maintenance"
    
    def export_to_csv(self, request, queryset):
        """Export selected maintenance records to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="maintenance_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Maintenance ID', 'Device ID', 'Device Brand', 'Device Model',
            'Type', 'Priority', 'Status', 'Start Date', 'Expected End Date',
            'Actual End Date', 'Estimated Cost', 'Actual Cost', 'Vendor',
            'Technician', 'Result', 'Created Date'
        ])
        
        for maintenance in queryset:
            writer.writerow([
                maintenance.maintenance_id,
                maintenance.device.device_id if maintenance.device else '',
                maintenance.device.brand if maintenance.device else '',
                maintenance.device.model if maintenance.device else '',
                maintenance.get_maintenance_type_display(),
                maintenance.get_priority_display(),
                maintenance.get_status_display(),
                maintenance.start_date.strftime('%Y-%m-%d') if maintenance.start_date else '',
                maintenance.expected_end_date.strftime('%Y-%m-%d') if maintenance.expected_end_date else '',
                maintenance.actual_end_date.strftime('%Y-%m-%d %H:%M') if maintenance.actual_end_date else '',
                maintenance.estimated_cost,
                maintenance.actual_cost or '',
                maintenance.vendor.name if maintenance.vendor else '',
                maintenance.technician_name or '',
                maintenance.get_result_display() if maintenance.result else '',
                maintenance.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    export_to_csv.short_description = "Export selected to CSV"
    
    def generate_maintenance_report(self, request, queryset):
        """Generate detailed maintenance report."""
        # Calculate statistics
        total_count = queryset.count()
        completed_count = queryset.filter(status='COMPLETED').count()
        in_progress_count = queryset.filter(status='IN_PROGRESS').count()
        overdue_count = sum(1 for m in queryset if m.is_overdue)
        
        total_cost = queryset.aggregate(Sum('actual_cost'))['actual_cost__sum'] or 0
        avg_cost = queryset.aggregate(Avg('actual_cost'))['actual_cost__avg'] or 0
        
        # Type distribution
        type_stats = queryset.values('maintenance_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Priority distribution
        priority_stats = queryset.values('priority').annotate(
            count=Count('id')
        ).order_by('-count')
        
        context = {
            'title': f'Maintenance Report - {total_count} Records',
            'total_count': total_count,
            'completed_count': completed_count,
            'in_progress_count': in_progress_count,
            'overdue_count': overdue_count,
            'total_cost': total_cost,
            'avg_cost': avg_cost,
            'type_stats': type_stats,
            'priority_stats': priority_stats,
            'maintenance_records': queryset[:50],  # Limit for display
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/maintenance/maintenance_report.html', context)
    generate_maintenance_report.short_description = "Generate detailed report"
    
    def schedule_follow_up(self, request, queryset):
        """Schedule follow-up maintenance for completed records."""
        scheduled = 0
        for maintenance in queryset.filter(status='COMPLETED', follow_up_required=True):
            if not maintenance.follow_up_date:
                # Suggest follow-up date based on maintenance type
                next_date = maintenance.get_next_maintenance_suggestion()
                if next_date:
                    maintenance.follow_up_date = next_date
                    maintenance.save()
                    scheduled += 1
        
        self.message_user(
            request,
            f'Follow-up scheduled for {scheduled} maintenance record(s).',
            messages.SUCCESS
        )
    schedule_follow_up.short_description = "Schedule follow-up maintenance"
    
    # Custom views
    def get_urls(self):
        """Add custom admin URLs."""
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.maintenance_dashboard), name='maintenance_dashboard'),
            path('overdue/', self.admin_site.admin_view(self.overdue_maintenance), name='maintenance_overdue'),
            path('cost-analysis/', self.admin_site.admin_view(self.cost_analysis), name='maintenance_cost_analysis'),
        ]
        return custom_urls + urls
    
    def maintenance_dashboard(self, request):
        """Custom maintenance dashboard view."""
        # Get statistics
        stats = Maintenance.get_maintenance_stats()
        
        # Recent maintenance
        recent_maintenance = Maintenance.objects.select_related('device', 'vendor').order_by('-created_at')[:10]
        
        # Overdue maintenance
        overdue_maintenance = Maintenance.objects.overdue().select_related('device')[:10]
        
        # Due soon
        due_soon = Maintenance.objects.due_soon().select_related('device')[:10]
        
        # Cost analysis
        monthly_costs = Maintenance.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=365)
        ).extra(
            select={'month': "DATE_FORMAT(created_at, '%%Y-%%m')"}
        ).values('month').annotate(
            total_cost=Sum('actual_cost'),
            count=Count('id')
        ).order_by('month')
        
        context = {
            'title': 'Maintenance Dashboard',
            'stats': stats,
            'recent_maintenance': recent_maintenance,
            'overdue_maintenance': overdue_maintenance,
            'due_soon': due_soon,
            'monthly_costs': monthly_costs,
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/maintenance/dashboard.html', context)
    
    def overdue_maintenance(self, request):
        """View for overdue maintenance."""
        overdue_list = Maintenance.objects.overdue().select_related('device', 'vendor')
        
        context = {
            'title': 'Overdue Maintenance',
            'overdue_list': overdue_list,
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/maintenance/overdue.html', context)
    
    def cost_analysis(self, request):
        """Cost analysis view."""
        # Cost by type
        cost_by_type = Maintenance.objects.values('maintenance_type').annotate(
            total_cost=Sum('actual_cost'),
            avg_cost=Avg('actual_cost'),
            count=Count('id')
        ).order_by('-total_cost')
        
        # Cost by vendor
        cost_by_vendor = Maintenance.objects.filter(vendor__isnull=False).values(
            'vendor__name'
        ).annotate(
            total_cost=Sum('actual_cost'),
            avg_cost=Avg('actual_cost'),
            count=Count('id')
        ).order_by('-total_cost')[:10]
        
        # Monthly cost trend
        monthly_trend = Maintenance.objects.filter(
            actual_cost__isnull=False,
            created_at__gte=timezone.now() - timedelta(days=365)
        ).extra(
            select={'month': "DATE_FORMAT(created_at, '%%Y-%%m')"}
        ).values('month').annotate(
            total_cost=Sum('actual_cost'),
            count=Count('id')
        ).order_by('month')
        
        context = {
            'title': 'Maintenance Cost Analysis',
            'cost_by_type': cost_by_type,
            'cost_by_vendor': cost_by_vendor,
            'monthly_trend': monthly_trend,
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/maintenance/cost_analysis.html', context)
    
    # Override methods
    def save_model(self, request, obj, form, change):
        """Custom save logic."""
        # Set created_by for new records
        if not change:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        
        super().save_model(request, obj, form, change)
        
        # Log significant status changes
        if change and 'status' in form.changed_data:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Maintenance {obj.maintenance_id} status changed to {obj.status} by {request.user.username}")
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'device',
            'vendor',
            'created_by',
            'approved_by'
        ).prefetch_related(
            'device__subcategory__category'
        )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize foreign key fields."""
        if db_field.name == "device":
            # Only show active devices
            kwargs["queryset"] = db_field.related_model.objects.filter(is_active=True)
        elif db_field.name == "vendor":
            # Only show active vendors
            kwargs["queryset"] = db_field.related_model.objects.filter(is_active=True)
        elif db_field.name == "approved_by":
            # Only show staff users who can approve
            kwargs["queryset"] = db_field.related_model.objects.filter(
                is_active=True,
                is_staff=True
            )
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def has_approve_permission(self, request):
        """Check if user has approval permission."""
        return request.user.has_perm('maintenance.approve_maintenance')
    
    def has_view_costs_permission(self, request):
        """Check if user can view cost information."""
        return request.user.has_perm('maintenance.view_maintenance_costs')
    
    def get_readonly_fields(self, request, obj=None):
        """Customize readonly fields based on permissions."""
        readonly_fields = list(self.readonly_fields)
        
        # Hide cost fields from users without permission
        if not self.has_view_costs_permission(request):
            readonly_fields.extend([
                'estimated_cost', 'actual_cost', 'parts_cost', 'labor_cost'
            ])
        
        # Make approval fields readonly for non-approvers
        if not self.has_approve_permission(request):
            readonly_fields.extend(['approved_by', 'approved_at'])
        
        return readonly_fields
    
    # Additional customizations
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions."""
        form = super().get_form(request, obj, **kwargs)
        
        # Hide internal notes from regular users
        if not request.user.has_perm('maintenance.view_internal_notes'):
            if 'internal_notes' in form.base_fields:
                del form.base_fields['internal_notes']
        
        return form


# Customize admin site headers and titles
admin.site.site_header = 'PIMS Administration - Bangladesh Parliament Secretariat'
admin.site.site_title = 'PIMS Maintenance Admin'
admin.site.index_title = 'Maintenance Management System'