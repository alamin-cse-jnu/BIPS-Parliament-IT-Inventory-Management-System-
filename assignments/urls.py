"""
URL Configuration for Assignments app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat

This module defines URL patterns for assignment management including:
- Assignment CRUD operations (list, create, edit, delete, detail)
- Assignment status filtering and search
- QR code operations and downloads
- Assignment returns and transfers
- Quick assignment workflow
- Export functionality

URL Structure:
/assignments/ - Main assignment management
/assignments/quick/ - Quick assignment workflow
/assignments/returns/ - Return management
/assignments/qr/ - QR code operations
"""

from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    # ============================================================================
    # Core Assignment Management
    # ============================================================================
    
    # Main assignment views
    path('', views.AssignmentListView.as_view(), name='list'),
    path('create/', views.AssignmentCreateView.as_view(), name='create'),
    path('<int:pk>/', views.AssignmentDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.AssignmentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.AssignmentDeleteView.as_view(), name='delete'),
    
    # ============================================================================
    # Status-based Assignment Views
    # ============================================================================
    
    path('active/', views.ActiveAssignmentsView.as_view(), name='active'),
    path('returned/', views.ReturnedAssignmentsView.as_view(), name='returned'),
    path('overdue/', views.OverdueAssignmentsView.as_view(), name='overdue'),
    path('cancelled/', views.CancelledAssignmentsView.as_view(), name='cancelled'),
    
    # ============================================================================
    # Quick Assignment Workflow
    # ============================================================================
    
    path('quick/', views.QuickAssignmentView.as_view(), name='quick'),
    path('quick/create/', views.QuickAssignmentCreateView.as_view(), name='quick_create'),
    
    # ============================================================================
    # Assignment Returns and Transfers
    # ============================================================================
    
    path('<int:pk>/return/', views.AssignmentReturnView.as_view(), name='return'),
    path('<int:pk>/transfer/', views.AssignmentTransferView.as_view(), name='transfer'),
    path('<int:pk>/extend/', views.AssignmentExtendView.as_view(), name='extend'),
    
    # ============================================================================
    # QR Code Operations
    # ============================================================================
    
    path('<int:pk>/qr/', views.AssignmentQRCodeView.as_view(), name='qr_code'),
    path('qr/<int:pk>/download/', views.AssignmentQRCodeDownloadView.as_view(), name='qr_download'),
    path('<int:pk>/qr/regenerate/', views.RegenerateQRCodeView.as_view(), name='qr_regenerate'),
    
    # ============================================================================
    # Search and Filtering
    # ============================================================================
    
    path('search/', views.AssignmentSearchView.as_view(), name='search'),
    path('filter/', views.AssignmentFilterView.as_view(), name='filter'),
    
    # ============================================================================
    # Export and Reports
    # ============================================================================
    
    path('export/', views.AssignmentExportView.as_view(), name='export'),
    path('export/csv/', views.AssignmentCSVExportView.as_view(), name='export_csv'),
    path('export/excel/', views.AssignmentExcelExportView.as_view(), name='export_excel'),
    path('export/pdf/', views.AssignmentPDFExportView.as_view(), name='export_pdf'),
    path('export/json/', views.AssignmentJSONExportView.as_view(), name='export_json'),
    path('reports/', views.AssignmentReportsView.as_view(), name='reports'),
]