"""
URL Configuration for Locations app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines URL patterns for location management including CRUD operations
for buildings, floors, blocks, rooms, offices, and comprehensive locations.
"""

from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    # ============================================================================
    # Location Management - Main Entity
    # ============================================================================
    
    # Location List and Management
    path('', views.LocationListView.as_view(), name='list'),
    path('create/', views.LocationCreateView.as_view(), name='create'),
    path('<int:pk>/', views.LocationDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.LocationUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.LocationDeleteView.as_view(), name='delete'),
    
    # Location Search and Filtering
    path('search/', views.LocationSearchView.as_view(), name='search'),
    path('filter/', views.LocationFilterView.as_view(), name='filter'),
    
    # Location Bulk Operations
    path('export/', views.LocationExportView.as_view(), name='export'),
    
    # GPS Coordinates Management
    path('<int:pk>/coordinates/', views.LocationCoordinatesView.as_view(), name='coordinates'),
    path('coordinates/map/', views.LocationMapView.as_view(), name='map'),
    path('coordinates/export/', views.CoordinatesExportView.as_view(), name='coordinates_export'),
    
    # Location Reports
    path('reports/', views.LocationReportsView.as_view(), name='reports'),
    path('reports/hierarchy/', views.LocationHierarchyReportView.as_view(), name='hierarchy_report'),
    path('reports/summary/', views.LocationSummaryReportView.as_view(), name='summary_report'),
    
    # ============================================================================
    # Building Management
    # ============================================================================
    
    path('buildings/', views.BuildingListView.as_view(), name='building_list'),
    path('buildings/create/', views.BuildingCreateView.as_view(), name='building_create'),
    path('buildings/<int:pk>/', views.BuildingDetailView.as_view(), name='building_detail'),
    path('buildings/<int:pk>/edit/', views.BuildingUpdateView.as_view(), name='building_edit'),
    path('buildings/<int:pk>/delete/', views.BuildingDeleteView.as_view(), name='building_delete'),
    
    # Building-specific operations
    path('buildings/<int:pk>/toggle-status/', views.BuildingToggleStatusView.as_view(), name='building_toggle_status'),
    
    # ============================================================================
    # Floor Management
    # ============================================================================
    
    path('floors/', views.FloorListView.as_view(), name='floor_list'),
    path('floors/create/', views.FloorCreateView.as_view(), name='floor_create'),
    path('floors/<int:pk>/', views.FloorDetailView.as_view(), name='floor_detail'),
    path('floors/<int:pk>/edit/', views.FloorUpdateView.as_view(), name='floor_edit'),
    path('floors/<int:pk>/delete/', views.FloorDeleteView.as_view(), name='floor_delete'),
    
    # Floor-specific operations
    path('floors/<int:pk>/toggle-status/', views.FloorToggleStatusView.as_view(), name='floor_toggle_status'),
    
    # ============================================================================
    # Block Management
    # ============================================================================
    
    path('blocks/', views.BlockListView.as_view(), name='block_list'),
    path('blocks/create/', views.BlockCreateView.as_view(), name='block_create'),
    path('blocks/<int:pk>/', views.BlockDetailView.as_view(), name='block_detail'),
    path('blocks/<int:pk>/edit/', views.BlockUpdateView.as_view(), name='block_edit'),
    path('blocks/<int:pk>/delete/', views.BlockDeleteView.as_view(), name='block_delete'),
    
    # Block-specific operations
    path('blocks/<int:pk>/toggle-status/', views.BlockToggleStatusView.as_view(), name='block_toggle_status'),
    
    # ============================================================================
    # Room Management
    # ============================================================================
    
    path('rooms/', views.RoomListView.as_view(), name='room_list'),
    path('rooms/create/', views.RoomCreateView.as_view(), name='room_create'),
    path('rooms/<int:pk>/', views.RoomDetailView.as_view(), name='room_detail'),
    path('rooms/<int:pk>/edit/', views.RoomUpdateView.as_view(), name='room_edit'),
    path('rooms/<int:pk>/delete/', views.RoomDeleteView.as_view(), name='room_delete'),
    
    # Room-specific operations
    path('rooms/<int:pk>/toggle-status/', views.RoomToggleStatusView.as_view(), name='room_toggle_status'),
    path('rooms/by-type/<str:room_type>/', views.RoomByTypeView.as_view(), name='rooms_by_type'),
    
    # ============================================================================
    # Office Management
    # ============================================================================
    
    path('offices/', views.OfficeListView.as_view(), name='office_list'),
    path('offices/create/', views.OfficeCreateView.as_view(), name='office_create'),
    path('offices/<int:pk>/', views.OfficeDetailView.as_view(), name='office_detail'),
    path('offices/<int:pk>/edit/', views.OfficeUpdateView.as_view(), name='office_edit'),
    path('offices/<int:pk>/delete/', views.OfficeDeleteView.as_view(), name='office_delete'),
    
    # Office-specific operations
    path('offices/<int:pk>/toggle-status/', views.OfficeToggleStatusView.as_view(), name='office_toggle_status'),
    path('offices/by-type/<str:office_type>/', views.OfficeByTypeView.as_view(), name='offices_by_type'),
    
    # ============================================================================
    # AJAX and API Endpoints
    # ============================================================================
    
    # Dynamic form data loading
    path('api/buildings/', views.BuildingAPIView.as_view(), name='api_buildings'),
    path('api/floors/', views.FloorAPIView.as_view(), name='api_floors'),
    path('api/blocks/', views.BlockAPIView.as_view(), name='api_blocks'),
    path('api/rooms/', views.RoomAPIView.as_view(), name='api_rooms'),
    path('api/offices/', views.OfficeAPIView.as_view(), name='api_offices'),
    
    # Location validation and lookup
    path('api/locations/validate-code/', views.LocationCodeValidationView.as_view(), name='api_validate_location_code'),
    path('api/locations/lookup/<str:code>/', views.LocationLookupView.as_view(), name='api_location_lookup'),
    path('api/locations/coordinates/', views.LocationCoordinatesAPIView.as_view(), name='api_location_coordinates'),
    
    # Building-specific lookups
    path('api/buildings/validate-code/', views.BuildingCodeValidationView.as_view(), name='api_validate_building_code'),
    path('api/buildings/lookup/<str:code>/', views.BuildingLookupView.as_view(), name='api_building_lookup'),
    
    # Office-specific lookups
    path('api/offices/validate-code/', views.OfficeCodeValidationView.as_view(), name='api_validate_office_code'),
    path('api/offices/lookup/<str:code>/', views.OfficeCodeLookupView.as_view(), name='api_office_lookup'),
    
    # ============================================================================
    # Dashboard and Analytics
    # ============================================================================
    
    path('dashboard/', views.LocationDashboardView.as_view(), name='dashboard'),
    path('analytics/', views.LocationAnalyticsView.as_view(), name='analytics'),
    path('statistics/', views.LocationStatisticsView.as_view(), name='statistics'),
    
    # Component statistics
    path('stats/buildings/', views.BuildingStatsView.as_view(), name='building_stats'),
    path('stats/floors/', views.FloorStatsView.as_view(), name='floor_stats'),
    path('stats/rooms/', views.RoomStatsView.as_view(), name='room_stats'),
    path('stats/offices/', views.OfficeStatsView.as_view(), name='office_stats'),
    
    # ============================================================================
    # Import and Export
    # ============================================================================
    
    # Import functionality
    path('import/', views.LocationImportView.as_view(), name='import'),
    path('import/buildings/', views.BuildingImportView.as_view(), name='building_import'),
    path('import/rooms/', views.RoomImportView.as_view(), name='room_import'),
    path('import/offices/', views.OfficeImportView.as_view(), name='office_import'),
    
    # Export functionality
    path('export/buildings/', views.BuildingExportView.as_view(), name='building_export'),
    path('export/floors/', views.FloorExportView.as_view(), name='floor_export'),
    path('export/blocks/', views.BlockExportView.as_view(), name='block_export'),
    path('export/rooms/', views.RoomExportView.as_view(), name='room_export'),
    path('export/offices/', views.OfficeExportView.as_view(), name='office_export'),
    
    # Comprehensive exports
    path('export/all/', views.AllLocationsExportView.as_view(), name='export_all'),
    path('export/template/', views.LocationTemplateExportView.as_view(), name='export_template'),
    
    # ============================================================================
    # QR Code Management
    # ============================================================================
    
    path('<int:pk>/qrcode/', views.LocationQRCodeView.as_view(), name='qrcode'),
    path('<int:pk>/qrcode/generate/', views.LocationQRCodeGenerateView.as_view(), name='qrcode_generate'),
    path('<int:pk>/qrcode/download/', views.LocationQRCodeDownloadView.as_view(), name='qrcode_download'),
    
    # Bulk QR code operations
    path('qrcodes/bulk-generate/', views.BulkQRCodeGenerateView.as_view(), name='bulk_qrcode_generate'),
    path('qrcodes/bulk-download/', views.BulkQRCodeDownloadView.as_view(), name='bulk_qrcode_download'),
    
    # ============================================================================
    # Utility Views
    # ============================================================================
    
    # Location hierarchy and relationships
    path('hierarchy/', views.LocationHierarchyView.as_view(), name='hierarchy'),
    path('relationships/', views.LocationRelationshipsView.as_view(), name='relationships'),
    
    # Location availability and status
    path('available/', views.AvailableLocationsView.as_view(), name='available'),
    path('inactive/', views.InactiveLocationsView.as_view(), name='inactive'),
    path('with-coordinates/', views.LocationsWithCoordinatesView.as_view(), name='with_coordinates'),
    path('without-coordinates/', views.LocationsWithoutCoordinatesView.as_view(), name='without_coordinates'),

]