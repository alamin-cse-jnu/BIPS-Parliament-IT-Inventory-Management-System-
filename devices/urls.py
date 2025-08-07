"""
URL patterns for Devices app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines URL routing for device management including:
- Device CRUD operations (list, create, edit, delete, detail)
- Category and subcategory management
- Device filtering and search
- QR code generation and download
- Warranty management
- Bulk operations and exports
- AJAX endpoints for dynamic functionality

URL Structure:
/devices/ - Main device management
/devices/categories/ - Category management  
/devices/subcategories/ - Subcategory management
/devices/warranties/ - Warranty management
/devices/qr/ - QR code operations
/devices/api/ - AJAX endpoints
"""

from django.urls import path, include
from . import views

app_name = 'devices'

# Device Management URLs
device_patterns = [
    # Main device views
    path('', views.DeviceListView.as_view(), name='list'),
    path('create/', views.DeviceCreateView.as_view(), name='create'),
    path('<int:pk>/', views.DeviceDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.DeviceUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.DeviceDeleteView.as_view(), name='delete'),
    
    # Device status views
    path('available/', views.AvailableDevicesView.as_view(), name='available'),
    path('assigned/', views.AssignedDevicesView.as_view(), name='assigned'), 
    path('maintenance/', views.MaintenanceDevicesView.as_view(), name='maintenance'),
    path('retired/', views.RetiredDevicesView.as_view(), name='retired'),
    
    # Device search and filter
    path('search/', views.DeviceSearchView.as_view(), name='search'),
    path('filter/', views.DeviceFilterView.as_view(), name='filter'),
    
    # Bulk operations
    path('bulk-update/', views.DeviceBulkUpdateView.as_view(), name='bulk_update'),
    path('bulk-export/', views.DeviceBulkExportView.as_view(), name='bulk_export'),
    
    # Device components
    path('<int:pk>/components/', views.DeviceComponentsView.as_view(), name='components'),
    path('<int:pk>/add-component/', views.AddComponentView.as_view(), name='add_component'),
]

# Category Management URLs
category_patterns = [
    path('', views.CategoryListView.as_view(), name='category_list'),
    path('create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
]

# Subcategory Management URLs
subcategory_patterns = [
    path('', views.SubcategoryListView.as_view(), name='subcategory_list'),
    path('create/', views.SubcategoryCreateView.as_view(), name='subcategory_create'),
    path('<int:pk>/', views.SubcategoryDetailView.as_view(), name='subcategory_detail'),
    path('<int:pk>/edit/', views.SubcategoryUpdateView.as_view(), name='subcategory_edit'),
    path('<int:pk>/delete/', views.SubcategoryDeleteView.as_view(), name='subcategory_delete'),
]

# Warranty Management URLs
warranty_patterns = [
    path('', views.WarrantyListView.as_view(), name='warranty_list'),
    path('create/', views.WarrantyCreateView.as_view(), name='warranty_create'),
    path('<int:pk>/', views.WarrantyDetailView.as_view(), name='warranty_detail'),
    path('<int:pk>/edit/', views.WarrantyUpdateView.as_view(), name='warranty_edit'),
    path('<int:pk>/delete/', views.WarrantyDeleteView.as_view(), name='warranty_delete'),
    
    # Warranty reports
    path('expiring/', views.ExpiringWarrantiesView.as_view(), name='warranty_expiring'),
    path('expired/', views.ExpiredWarrantiesView.as_view(), name='warranty_expired'),
]

# QR Code URLs
qr_patterns = [
    path('', views.QRCodeListView.as_view(), name='qr_list'),
    path('<int:device_pk>/generate/', views.GenerateQRCodeView.as_view(), name='qr_generate'),
    path('<int:pk>/download/', views.DownloadQRCodeView.as_view(), name='qr_download'),
    path('<int:pk>/view/', views.ViewQRCodeView.as_view(), name='qr_view'),
    path('bulk-generate/', views.BulkGenerateQRView.as_view(), name='qr_bulk_generate'),
    path('bulk-download/', views.BulkDownloadQRView.as_view(), name='qr_bulk_download'),
]

# AJAX API endpoints for dynamic functionality
api_patterns = [
    # Dynamic form data
    path('subcategories/<int:category_id>/', views.get_subcategories_ajax, name='api_subcategories'),
    path('parent-devices/<int:subcategory_id>/', views.get_parent_devices_ajax, name='api_parent_devices'),
    path('device-info/<int:device_id>/', views.get_device_info_ajax, name='api_device_info'),
    
    # Specifications templates
    path('spec-template/<int:subcategory_id>/', views.get_specifications_template_ajax, name='api_spec_template'),
    path('spec-examples/', views.get_specifications_examples_ajax, name='api_spec_examples'),
    
    # Validation
    path('validate-device-id/', views.validate_device_id_ajax, name='api_validate_device_id'),
    path('validate-serial/', views.validate_serial_number_ajax, name='api_validate_serial'),
    
    # Statistics
    path('dashboard-stats/', views.get_dashboard_stats_ajax, name='api_dashboard_stats'),
    path('category-stats/<int:category_id>/', views.get_category_stats_ajax, name='api_category_stats'),
]

# Reports URLs
reports_patterns = [
    path('', views.DeviceReportsView.as_view(), name='reports'),
    path('inventory/', views.InventoryReportView.as_view(), name='report_inventory'),
    path('by-category/', views.CategoryReportView.as_view(), name='report_category'),
    path('by-location/', views.LocationReportView.as_view(), name='report_location'),
    path('by-vendor/', views.VendorReportView.as_view(), name='report_vendor'),
    path('depreciation/', views.DepreciationReportView.as_view(), name='report_depreciation'),
    path('warranty-summary/', views.WarrantyReportView.as_view(), name='report_warranty'),
    
    # Export formats
    path('export/excel/', views.ExportDevicesExcelView.as_view(), name='export_excel'),
    path('export/pdf/', views.ExportDevicesPDFView.as_view(), name='export_pdf'),
    path('export/csv/', views.ExportDevicesCSVView.as_view(), name='export_csv'),
]

# Dashboard URLs
dashboard_patterns = [
    path('', views.DeviceDashboardView.as_view(), name='dashboard'),
    path('summary/', views.DeviceSummaryView.as_view(), name='summary'),
    path('alerts/', views.DeviceAlertsView.as_view(), name='alerts'),
]

# Main URL patterns
urlpatterns = [
    # Dashboard
    path('dashboard/', include(dashboard_patterns)),
    
    # Core device management
    path('', include(device_patterns)),
    
    # Category management
    path('categories/', include(category_patterns)),
    
    # Subcategory management  
    path('subcategories/', include(subcategory_patterns)),
    
    # Warranty management
    path('warranties/', include(warranty_patterns)),
    
    # QR code management
    path('qr/', include(qr_patterns)),
    
    # Reports
    path('reports/', include(reports_patterns)),
    
    # AJAX API endpoints
    path('api/', include(api_patterns)),
]