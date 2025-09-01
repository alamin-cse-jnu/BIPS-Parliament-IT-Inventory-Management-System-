# users/urls.py
# ============================================================================
# PIMS-PRP Integration - Bangladesh Parliament Secretariat
# Location: Dhaka, Bangladesh
# 
# URL Configuration for User Management with PRP API Integration
# Supports both local PIMS users and PRP-synced users
# Following template design pattern rule: flat design, high contrast
# ============================================================================

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

# ============================================================================
# PRP Integration URL Patterns (Admin-only, secure endpoints)
# ============================================================================
prp_patterns = [
    # ✅ CORRECTED: These match your frontend calls exactly
    path('departments/', views.prp_departments_api, name='prp_departments'),
    path('lookup/<str:employee_id>/', views.prp_lookup_employee, name='prp_lookup'),
    
    # PRP Dashboard and Control Panel
    path('dashboard/', views.PRPSyncDashboardView.as_view(), name='prp_sync_dashboard'),
    path('sync/trigger/', views.PRPSyncTriggerView.as_view(), name='prp_sync_trigger'),
    # Commented out - implement these views when needed
    # path('sync/status/', views.PRPSyncStatusView.as_view(), name='prp_sync_status'),
    # path('health/', views.PRPHealthCheckView.as_view(), name='prp_health_check'),
    # path('departments/<int:department_id>/sync/', views.PRPSyncDepartmentUsersView.as_view(), name='prp_sync_department_users'),
    # path('sync/reports/', views.PRPSyncReportsView.as_view(), name='prp_sync_reports'),
    # path('sync/logs/', views.PRPSyncLogsView.as_view(), name='prp_sync_logs'),
]

# ============================================================================
# Authentication Patterns (Enhanced for PRP Integration)
# ============================================================================
auth_patterns = [
    # Login (supports both PIMS local users and PRP User ID as username)
    path('login/', views.CustomLoginView.as_view(), name='auth_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='auth_logout'),
    
    # Password Reset URLs (for local users only)
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='auth_password_reset'),
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

# ============================================================================
# Core User Management Patterns (Preserved - No Breaking Changes)
# ============================================================================
user_management_patterns = [
    # User CRUD Operations
    path('', views.UserListView.as_view(), name='manage_list'),
    path('create/', views.UserCreateView.as_view(), name='manage_create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='manage_detail'),
    path('<int:pk>/edit/', views.UserUpdateView.as_view(), name='manage_edit'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='manage_delete'),
    
    # Role and Permission Management
    path('<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='manage_roles'),
    path('<int:pk>/permissions/', views.UserPermissionView.as_view(), name='manage_permissions'),
    
    # User Status Management (commented out - implement when needed)
    # path('<int:pk>/activate/', views.UserActivateView.as_view(), name='manage_activate'),
    # path('<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='manage_deactivate'),
]

# ============================================================================
# User Profile Management
# ============================================================================
profile_patterns = [
    path('', views.UserProfileView.as_view(), name='profile'),
    path('edit/', views.UserProfileEditView.as_view(), name='profile_edit'),
    path('password/', views.UserPasswordChangeView.as_view(), name='password_change'),
]

# ============================================================================
# Search, Reporting, and Analytics
# ============================================================================
search_reporting_patterns = [
    # User Search and Filtering (supports both local and PRP users)
    path('search/', views.UserSearchView.as_view(), name='search'),
    
    # Employee ID Lookup (supports both local and PRP employee IDs)
    path('lookup/<str:employee_id>/', views.user_lookup_by_employee_id, name='lookup'),
    
    # User Reports and Analytics
    path('', views.UserReportsView.as_view(), name='reports'),
]

# ============================================================================
# AJAX API Endpoints
# ============================================================================
api_patterns = [
    # Employee lookup AJAX endpoints
    path('employee/<str:employee_id>/', views.lookup_user_by_employee_id_ajax, name='employee_lookup'),
    
    # PRP-specific API endpoints
    path('prp-check/<str:employee_id>/', views.check_prp_user_exists, name='prp_user_check'),
    
    # Future API endpoints (commented out - implement when needed)
    # path('prp-departments/', views.get_prp_departments_ajax, name='api_prp_departments'),
    # path('prp-sync-progress/', views.get_prp_sync_progress, name='api_prp_sync_progress'),
]

# ============================================================================
# Main URL Patterns - Complete Structure
# ============================================================================
urlpatterns = [
    # ========================================================================
    # PRP Integration Routes (Admin-only, secured) - MUST BE FIRST
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
    # Direct URL Access (maintains existing structure for backward compatibility)
    # ========================================================================
    
    # Main user management URLs
    path('', views.UserListView.as_view(), name='list'),
    path('create/', views.UserCreateView.as_view(), name='create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='delete'),
    
    # User Roles and Permissions
    path('<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='roles'),
    path('<int:pk>/permissions/', views.UserPermissionView.as_view(), name='permissions'),
    
    # Legacy Support and Backward Compatibility
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('lookup/<str:employee_id>/', views.user_lookup_by_employee_id, name='lookup'),
]

# ============================================================================
# URL Pattern Summary for PIMS-PRP Integration
# ============================================================================
"""
✅ CORRECTED URLs that match your frontend expectations:

PRP Integration URLs (Admin-only):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• /users/prp/departments/                   - Get PRP departments (AJAX)
• /users/prp/lookup/110100092/              - Lookup employee in PRP (AJAX)
• /users/prp/dashboard/                     - PRP sync dashboard
• /users/prp/sync/trigger/                  - Manual sync trigger

Authentication URLs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• /users/login/                             - Login (supports PRP User ID)
• /users/logout/                            - Logout
• /users/auth/login/                        - Enhanced login
• /users/auth/password-reset/               - Password reset

User Management URLs (Preserved):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• /users/                                   - User list (shows both local & PRP)
• /users/create/                            - Create new user (local only)
• /users/<pk>/                              - User detail
• /users/<pk>/edit/                         - Edit user (PRP fields read-only)
• /users/<pk>/delete/                       - Delete user
• /users/<pk>/roles/                        - Manage user roles
• /users/<pk>/permissions/                  - Manage permissions

AJAX API URLs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• /users/api/employee/<employee_id>/        - Employee lookup AJAX
• /users/api/prp-check/<employee_id>/       - PRP user check AJAX

Profile & Search URLs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• /users/profile/                           - User profile
• /users/reports/search/                    - User search
• /users/lookup/<employee_id>/              - Employee lookup
• /users/reports/                           - User reports

Key Features:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PRP URLs positioned FIRST to avoid conflicts
✅ All existing URLs preserved for backward compatibility  
✅ Template design pattern: flat design, high contrast
✅ Location context: Bangladesh Parliament Secretariat, Dhaka
✅ Admin-only PRP routes with proper security
✅ One-way sync: PRP → PIMS business rules maintained
"""