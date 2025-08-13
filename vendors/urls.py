"""
URL Configuration for Vendors app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines URL patterns for essential vendor management operations.
"""

from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    # ============================================================================
    # Basic CRUD Operations
    # ============================================================================
    
    # Vendor List and Management
    path('', views.VendorListView.as_view(), name='list'),
    path('create/', views.VendorCreateView.as_view(), name='create'),
    path('<int:pk>/', views.VendorDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.VendorUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.VendorDeleteView.as_view(), name='delete'),
    
    # ============================================================================
    # Search and Filtering
    # ============================================================================
    
    # Search functionality
    path('search/', views.VendorSearchView.as_view(), name='search'),
    
    # Basic filtering by type and status
    path('active/', views.VendorActiveListView.as_view(), name='active'),
    path('inactive/', views.VendorInactiveListView.as_view(), name='inactive'),
    path('preferred/', views.VendorPreferredListView.as_view(), name='preferred'),
    path('suppliers/', views.VendorSupplierListView.as_view(), name='suppliers'),
    path('service-providers/', views.VendorServiceProviderListView.as_view(), name='service_providers'),
    
    # ============================================================================
    # Reports and Export
    # ============================================================================
    
    # Reports
    path('reports/', views.VendorReportsView.as_view(), name='reports'),
    path('summary/', views.VendorSummaryView.as_view(), name='summary'),
    
    # Export
    path('export/csv/', views.VendorExportCSVView.as_view(), name='export_csv'),
    path('export/contacts/', views.VendorContactExportView.as_view(), name='export_contacts'),
    
    # ============================================================================
    # Quick Actions
    # ============================================================================
    
    # Status changes
    path('<int:pk>/activate/', views.vendor_activate, name='activate'),
    path('<int:pk>/deactivate/', views.vendor_deactivate, name='deactivate'),
    path('<int:pk>/toggle-preferred/', views.vendor_toggle_preferred, name='toggle_preferred'),
    
    # AJAX endpoints for form validation and search
    path('api/validate-code/', views.vendor_validate_code, name='validate_code'),
    path('api/search/', views.vendor_search_api, name='search_api'),
]