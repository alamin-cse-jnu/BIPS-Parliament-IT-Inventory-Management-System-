"""
URL Configuration for Maintenance app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines URL patterns for maintenance management including:
- Maintenance CRUD operations (list, create, edit, delete, detail)
- Maintenance scheduling and quick actions
- Status filtering and search functionality
- Reports and analytics
- Approval workflows
- Export functionality

URL Structure:
/maintenance/ - Main maintenance management
/maintenance/schedule/ - Maintenance scheduling
/maintenance/reports/ - Reports and analytics
/maintenance/api/ - AJAX endpoints
"""

from django.urls import path, include
from . import views

app_name = 'maintenance'

# Core Maintenance Management URLs
maintenance_patterns = [
    # Main maintenance views
    path('', views.MaintenanceListView.as_view(), name='list'),
    path('create/', views.MaintenanceCreateView.as_view(), name='create'),
    path('<int:pk>/', views.MaintenanceDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.MaintenanceUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.MaintenanceDeleteView.as_view(), name='delete'),
    
    # Status-based views
    path('scheduled/', views.ScheduledMaintenanceView.as_view(), name='scheduled'),
    path('in-progress/', views.InProgressMaintenanceView.as_view(), name='in_progress'),
    path('completed/', views.CompletedMaintenanceView.as_view(), name='completed'),
    path('overdue/', views.OverdueMaintenanceView.as_view(), name='overdue'),
    path('cancelled/', views.CancelledMaintenanceView.as_view(), name='cancelled'),
    
    # Search and filtering
    path('search/', views.MaintenanceSearchView.as_view(), name='search'),
    path('filter/', views.MaintenanceFilterView.as_view(), name='filter'),
    
    # Bulk operations
    path('bulk-update/', views.MaintenanceBulkUpdateView.as_view(), name='bulk_update'),
    path('bulk-export/', views.MaintenanceBulkExportView.as_view(), name='bulk_export'),
]

# Maintenance Scheduling URLs
schedule_patterns = [
    path('', views.MaintenanceScheduleView.as_view(), name='schedule_create'),
    path('recurring/', views.RecurringMaintenanceView.as_view(), name='schedule_recurring'),
    path('calendar/', views.MaintenanceCalendarView.as_view(), name='calendar'),
    path('upcoming/', views.UpcomingMaintenanceView.as_view(), name='upcoming'),
    path('due-soon/', views.DueSoonMaintenanceView.as_view(), name='due_soon'),
]

# Quick Actions URLs (for device integration)
quick_action_patterns = [
    path('device/<int:device_id>/', views.DeviceMaintenanceView.as_view(), name='device_maintenance'),
    path('quick-schedule/', views.QuickScheduleView.as_view(), name='quick_schedule'),
    path('report-issue/', views.ReportIssueView.as_view(), name='report_issue'),
]



# Status Change URLs
status_patterns = [
    path('<int:pk>/start/', views.StartMaintenanceView.as_view(), name='start'),
    path('<int:pk>/complete/', views.CompleteMaintenanceView.as_view(), name='complete'),
    path('<int:pk>/cancel/', views.CancelMaintenanceView.as_view(), name='cancel'),
    path('<int:pk>/hold/', views.HoldMaintenanceView.as_view(), name='hold'),
    path('<int:pk>/resume/', views.ResumeMaintenanceView.as_view(), name='resume'),
]

# Reports and Analytics URLs
reports_patterns = [
    path('', views.MaintenanceReportsView.as_view(), name='reports_home'),
    path('summary/', views.MaintenanceSummaryReportView.as_view(), name='report_summary'),
    path('cost-analysis/', views.MaintenanceCostAnalysisView.as_view(), name='report_cost'),
    path('performance/', views.MaintenancePerformanceReportView.as_view(), name='report_performance'),
    path('vendor-analysis/', views.VendorPerformanceReportView.as_view(), name='report_vendor'),
    path('device-history/', views.DeviceMaintenanceHistoryView.as_view(), name='report_device_history'),
    path('trends/', views.MaintenanceTrendsReportView.as_view(), name='report_trends'),
    
    # Export formats
    path('export/pdf/', views.ExportMaintenancePDFView.as_view(), name='export_pdf'),
    path('export/excel/', views.ExportMaintenanceExcelView.as_view(), name='export_excel'),
    path('export/csv/', views.ExportMaintenanceCSVView.as_view(), name='export_csv'),
]

# Dashboard URLs
dashboard_patterns = [
    path('', views.MaintenanceDashboardView.as_view(), name='dashboard'),
    path('alerts/', views.MaintenanceAlertsView.as_view(), name='alerts'),
    path('statistics/', views.MaintenanceStatisticsView.as_view(), name='statistics'),
]

# AJAX API Endpoints
api_patterns = [
    # Form validation and auto-completion
    path('validate-device/', views.validate_device_maintenance, name='api_validate_device'),
    path('suggest-cost/', views.suggest_maintenance_cost, name='api_suggest_cost'),
    path('vendor-search/', views.vendor_search_api, name='api_vendor_search'),
    
    # Dynamic form updates
    path('device-info/<int:device_id>/', views.get_device_info, name='api_device_info'),
    path('maintenance-history/<int:device_id>/', views.get_maintenance_history, name='api_maintenance_history'),
    path('cost-estimate/', views.get_cost_estimate, name='api_cost_estimate'),
    
    # Status updates
    path('<int:pk>/update-status/', views.update_maintenance_status, name='api_update_status'),
    path('<int:pk>/progress/', views.get_maintenance_progress, name='api_progress'),
    
    # Calendar data
    path('calendar-events/', views.get_calendar_events, name='api_calendar_events'),
    path('calendar-month/<int:year>/<int:month>/', views.get_month_events, name='api_month_events'),
    
    # Dashboard data
    path('dashboard-stats/', views.get_dashboard_stats, name='api_dashboard_stats'),
    path('overdue-count/', views.get_overdue_count, name='api_overdue_count'),

    # Essential AJAX endpoints
    path('<int:pk>/quick-status/', views.quick_status_update, name='quick_status'),
    path('api/check-device/', views.device_maintenance_check, name='check_device'),
    path('api/estimate-cost/', views.simple_cost_estimate, name='estimate_cost'),
    
    # Simple export
    path('export/simple-csv/', views.export_maintenance_simple_csv, name='simple_csv'),
]

# Main URL patterns
urlpatterns = [
    # Dashboard
    path('dashboard/', include(dashboard_patterns)),
    
    # Core maintenance management
    path('', include(maintenance_patterns)),
    
    # Maintenance scheduling
    path('schedule/', include(schedule_patterns)),
    
    # Quick actions
    path('actions/', include(quick_action_patterns)),
    
    # Status changes
    path('status/', include(status_patterns)),
    
    # Reports and analytics
    path('reports/', include(reports_patterns)),
    
    # AJAX API endpoints
    path('api/', include(api_patterns)),
]