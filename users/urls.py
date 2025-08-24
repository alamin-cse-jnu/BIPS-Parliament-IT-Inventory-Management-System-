"""
URL Configuration for Users app in PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat, Dhaka, Bangladesh

This module defines URL patterns for user management and PRP (Parliament Resource Portal) 
integration including:
- Standard user CRUD operations (list, create, edit, delete, detail)
- User authentication (login, logout, password management)
- PRP synchronization operations (admin-controlled)
- PRP user lookup and status checking
- User search, filtering, and reporting
- Role and permission management

PRP Integration URLs (New - Admin Only):
- PRP sync dashboard and management
- Department synchronization from PRP API
- User lookup by PRP employee ID
- Sync status monitoring and reporting
- Individual and bulk user synchronization

Location: Bangladesh Parliament Secretariat, Dhaka
Project: PIMS-PRP Integration
API Integration: https://prp.parliament.gov.bd (Parliament Resource Portal)
"""

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

# ============================================================================
# PRP (Parliament Resource Portal) Integration URLs - Admin Only
# ============================================================================

prp_patterns = [
    # PRP Sync Dashboard - Main control panel for PRP operations
    path('dashboard/', views.PRPSyncDashboardView.as_view(), name='prp_sync_dashboard'),
    
    # PRP Sync Operations (Admin-controlled one-way sync PRP → PIMS)
    path('sync/trigger/', views.prp_sync_trigger, name='prp_sync_trigger'),
    path('sync/status/', views.prp_sync_status, name='prp_sync_status'),
    path('sync/departments/', views.prp_sync_departments, name='prp_sync_departments'),
    
    # Department Management from PRP
    path('departments/', views.prp_departments_api, name='prp_departments_api'),
    path('departments/refresh/', views.prp_departments_refresh, name='prp_departments_refresh'),
    
    # PRP User Lookup and Management
    path('lookup/<str:employee_id>/', views.prp_user_lookup, name='prp_user_lookup'),
    # path('search/', views.prp_user_search, name='prp_user_search'),
    
    # Individual User Sync Operations
    path('<int:pk>/sync/', views.prp_sync_single_user, name='prp_sync_single_user'),
    # path('<int:pk>/sync/force/', views.prp_force_sync_single_user, name='prp_force_sync_user'),
    
    # Bulk Operations
    path('sync/bulk/', views.prp_bulk_sync_users, name='prp_bulk_sync'),
    path('sync/department/<int:department_id>/', views.prp_sync_department_users, name='prp_sync_department'),
    
    # PRP Status and Health Check
    #path('health/', views.prp_health_check, name='prp_health_check'),
    #path('api-status/', views.prp_api_status, name='prp_api_status'),
    
    # PRP Reports and Analytics
    path('reports/', views.prp_sync_reports, name='prp_sync_reports'),
    path('reports/sync-history/', views.prp_sync_history, name='prp_sync_history'),
    #path('reports/errors/', views.prp_error_reports, name='prp_error_reports'),
]

# ============================================================================
# Standard User Management URLs (Existing - Preserved)
# ============================================================================

# Core user management patterns
user_management_patterns = [
    # User List and Management
    path('', views.UserListView.as_view(), name='list'),
    path('create/', views.UserCreateView.as_view(), name='create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='delete'),
    
    # Role and Permission Management
    path('<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='roles'),
    path('<int:pk>/permissions/', views.UserPermissionView.as_view(), name='permissions'),
    
    # User Status Management
    path('<int:pk>/activate/', views.UserActivateView.as_view(), name='activate'),
    path('<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='deactivate'),
]

# User profile management patterns
profile_patterns = [
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/edit/', views.UserProfileEditView.as_view(), name='profile_edit'),
    path('profile/password/', views.UserPasswordChangeView.as_view(), name='password_change'),
]

# Authentication patterns (supports both PIMS local and PRP users)
auth_patterns = [
    # Login (supports PRP User ID as username)
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='logout'),
    
    # Password Reset URLs
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html'
         ), name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ), name='password_reset_complete'),
]

# Search and reporting patterns
search_reporting_patterns = [
    # User Search and Filtering
    path('search/', views.UserSearchView.as_view(), name='search'),
    path('filter/', views.UserFilterView.as_view(), name='filter'),
    
    # Employee ID Lookup (AJAX endpoint - supports both local and PRP users)
    path('lookup/<str:employee_id>/', views.user_lookup_by_employee_id, name='lookup'),
    
    # User Reports and Analytics
    path('reports/', views.UserReportsView.as_view(), name='reports'),
    #path('export/', views.UserExportView.as_view(), name='export'),
    #path('statistics/', views.UserStatisticsView.as_view(), name='statistics'),
]

# AJAX API endpoints for dynamic functionality
api_patterns = [
    # User data endpoints
    # path('api/user-info/<int:user_id>/', views.get_user_info_ajax, name='api_user_info'),
    # path('api/validate-employee-id/', views.validate_employee_id_ajax, name='api_validate_employee_id'),
    # path('api/validate-username/', views.validate_username_ajax, name='api_validate_username'),
    
    # # PRP-specific API endpoints
    # path('api/prp-user-check/<str:employee_id>/', views.check_prp_user_exists, name='api_prp_user_check'),
    # path('api/prp-departments/', views.get_prp_departments_ajax, name='api_prp_departments'),
    # path('api/prp-sync-progress/', views.get_prp_sync_progress, name='api_prp_sync_progress'),
    
    # # Dashboard statistics
    # path('api/user-stats/', views.get_user_statistics_ajax, name='api_user_stats'),
    # path('api/prp-stats/', views.get_prp_statistics_ajax, name='api_prp_stats'),
]

# ============================================================================
# Main URL Patterns - Combined Structure
# ============================================================================

urlpatterns = [
    # ========================================================================
    # PRP Integration Routes (Admin-only, secured)
    # ========================================================================
    path('prp/', include(prp_patterns)),
    
    # ========================================================================
    # Authentication (supports both PIMS local and PRP users)
    # ========================================================================
    path('auth/', include(auth_patterns)),
    
    # Direct login/logout for convenience (maintains existing URLs)
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='logout'),
    
    # ========================================================================
    # User Management (Core PIMS functionality - preserved)
    # ========================================================================
    path('manage/', include(user_management_patterns)),
    
    # Direct user management URLs (maintains existing structure)
    path('', views.UserListView.as_view(), name='list'),
    path('create/', views.UserCreateView.as_view(), name='create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='delete'),
    
    # ========================================================================
    # User Roles and Permissions
    # ========================================================================
    path('<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='roles'),
    path('<int:pk>/permissions/', views.UserPermissionView.as_view(), name='permissions'),
    path('<int:pk>/activate/', views.UserActivateView.as_view(), name='activate'),
    path('<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='deactivate'),
    
    # ========================================================================
    # User Profile Management
    # ========================================================================
    path('profile/', include(profile_patterns)),
    
    # ========================================================================
    # Search, Reporting, and Analytics
    # ========================================================================
    path('reports/', include(search_reporting_patterns)),
    
    # ========================================================================
    # AJAX API Endpoints
    # ========================================================================
    path('api/', include(api_patterns)),
    
    # ========================================================================
    # Legacy Support and Backward Compatibility
    # ========================================================================
    
    # Password reset (direct access)
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    
    # Employee lookup (backward compatibility)
    path('lookup/<str:employee_id>/', views.user_lookup_by_employee_id, name='lookup'),
    
   
]

# ============================================================================
# URL Pattern Summary for PIMS-PRP Integration
# ============================================================================
"""
New PRP Integration URLs (Admin-only):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dashboard & Management:
• /users/prp/dashboard/                     - PRP sync control panel
• /users/prp/sync/trigger/                  - Manual sync trigger
• /users/prp/sync/status/                   - Sync operation status
• /users/prp/health/                        - PRP API health check

Department Operations:
• /users/prp/departments/                   - List PRP departments
• /users/prp/departments/refresh/           - Refresh department cache
• /users/prp/sync/departments/              - Sync departments from PRP

User Lookup & Search:
• /users/prp/lookup/<employee_id>/          - PRP user lookup by ID
• /users/prp/search/                        - Search PRP users

Individual User Operations:
• /users/<pk>/prp/sync/                     - Sync specific user from PRP
• /users/<pk>/prp/sync/force/               - Force sync user (ignore cache)

Bulk Operations:
• /users/prp/sync/bulk/                     - Bulk user synchronization
• /users/prp/sync/department/<dept_id>/     - Sync all users from department

Reports & Analytics:
• /users/prp/reports/                       - PRP sync reports
• /users/prp/reports/sync-history/          - Sync operation history
• /users/prp/reports/errors/                - Error reports and troubleshooting

AJAX API Endpoints:
• /users/api/prp-user-check/<employee_id>/  - Check if user exists in PRP
• /users/api/prp-departments/               - Get departments via AJAX
• /users/api/prp-sync-progress/             - Real-time sync progress
• /users/api/prp-stats/                     - PRP integration statistics

Authentication (Enhanced for PRP):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• /users/login/                             - Supports PRP User ID login
• /users/auth/login/                        - Alternative login URL

Security Notes:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- All PRP routes require admin permissions
- PRP API uses token-based authentication
- One-way sync: PRP → PIMS (PRP is authoritative)
- Existing PIMS functionality remains unchanged
- Admin can override user status (business rule)

Dependencies:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- users.views (all PRP view functions)
- users.api.prp_client (PRP API client)
- users.api.sync_service (sync business logic)
- users.api.exceptions (custom PRP exceptions)
"""