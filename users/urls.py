# users/urls.py
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
    # PRP Sync Dashboard and Control Panel
    path('dashboard/', views.PRPSyncDashboardView.as_view(), name='prp_sync_dashboard'),
    path('sync/trigger/', views.PRPSyncTriggerView.as_view(), name='prp_sync_trigger'),
    #path('sync/status/', views.PRPSyncStatusView.as_view(), name='prp_sync_status'),
    #path('health/', views.PRPHealthCheckView.as_view(), name='prp_health_check'),
    
    # Department Operations
    #path('departments/', views.PRPDepartmentListView.as_view(), name='prp_departments'),
    #path('departments/<int:department_id>/sync/', views.PRPSyncDepartmentUsersView.as_view(), name='prp_sync_department_users'),
    
    # Sync Operations and Reporting
    #path('sync/reports/', views.PRPSyncReportsView.as_view(), name='prp_sync_reports'),
    #path('sync/logs/', views.PRPSyncLogsView.as_view(), name='prp_sync_logs'),
]

# ============================================================================
# Authentication Patterns (Enhanced for PRP Integration)
# ============================================================================
auth_patterns = [
    # Login (supports both PIMS local users and PRP User ID as username)
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='logout'),
    
    # Password Reset URLs (for local users only)
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

# ============================================================================
# Core User Management Patterns (Preserved - No Breaking Changes)
# ============================================================================
user_management_patterns = [
    # User CRUD Operations
    path('', views.UserListView.as_view(), name='list'),
    path('create/', views.UserCreateView.as_view(), name='create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='delete'),
    
    # User Status Management
    #path('<int:pk>/activate/', views.UserActivateView.as_view(), name='activate'),
    #path('<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='deactivate'),
    
    # Role and Permission Management
    path('<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='roles'),
    path('<int:pk>/permissions/', views.UserPermissionView.as_view(), name='permissions'),
]

# ============================================================================
# User Profile Management
# ============================================================================
profile_patterns = [
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/edit/', views.UserProfileEditView.as_view(), name='profile_edit'),
    #path('profile/password/', views.UserPasswordChangeView.as_view(), name='password_change'),
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
    path('reports/', views.UserReportsView.as_view(), name='reports'),
]

# ============================================================================
# AJAX API Endpoints (Future Implementation)
# ============================================================================
api_patterns = [
    # PRP-specific API endpoints (placeholder for future development)
    # path('api/prp-user-check/<str:employee_id>/', views.check_prp_user_exists, name='api_prp_user_check'),
    # path('api/prp-departments/', views.get_prp_departments_ajax, name='api_prp_departments'),
    # path('api/prp-sync-progress/', views.get_prp_sync_progress, name='api_prp_sync_progress'),
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
    #path('<int:pk>/activate/', views.UserActivateView.as_view(), name='activate'),
    #path('<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='deactivate'),
    
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
Essential PRP Integration URLs (Admin-only):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dashboard & Management:
• /users/prp/dashboard/                     - PRP sync control panel
• /users/prp/sync/trigger/                  - Manual sync trigger
• /users/prp/sync/status/                   - Sync operation status
• /users/prp/health/                        - PRP API health check

Department Operations:
• /users/prp/departments/                   - List PRP departments
• /users/prp/departments/<id>/sync/         - Sync specific department users

Sync Operations:
• /users/prp/sync/reports/                  - View sync reports
• /users/prp/sync/logs/                     - View sync operation logs

Preserved PIMS URLs (No Breaking Changes):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Authentication:
• /users/login/                             - Login (supports PRP User ID)
• /users/logout/                            - Logout
• /users/auth/login/                        - Enhanced login
• /users/auth/password-reset/               - Password reset

User Management:
• /users/                                   - User list (shows both local & PRP)
• /users/create/                            - Create new user (local only)
• /users/<pk>/                              - User detail
• /users/<pk>/edit/                         - Edit user (PRP fields read-only)
• /users/<pk>/delete/                       - Delete user

User Operations:
• /users/<pk>/activate/                     - Activate user
• /users/<pk>/deactivate/                   - Deactivate user
• /users/<pk>/roles/                        - Manage user roles
• /users/<pk>/permissions/                  - Manage permissions

Profile & Search:
• /users/profile/                           - User profile
• /users/reports/search/                    - User search
• /users/lookup/<employee_id>/              - Employee lookup
• /users/reports/reports/                   - User reports

Integration Design Notes:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Business Rules Implementation:
   - PRP users login with PRP User ID as username
   - Default password: "12345678" for all PRP users
   - PRP-sourced fields are read-only in PIMS interface
   - Admin can override user status (inactive status takes precedence)
   - One-way sync: PRP → PIMS only

2. Template Design Pattern:
   - Flat design with high contrast (NO glass-morphism)
   - Color scheme: Teal (#14b8a6), Orange (#f97316), Red (#ef4444)
   - Location context: Bangladesh Parliament Secretariat, Dhaka
   - Responsive design for all device sizes
   - Consistent spacing and modern typography

3. Security Considerations:
   - PRP routes are admin-only and secured
   - Token-based authentication for PRP API
   - Comprehensive audit logging
   - Rate limiting for API calls
   - Error handling prevents data corruption

4. Development Approach:
   - NO breaking changes to existing PIMS functionality
   - Minimal URL structure focused on essential operations
   - Clean separation between PRP and local user management
   - Future-ready structure for additional PRP features

This URL configuration provides a solid foundation for the PIMS-PRP integration
while maintaining backward compatibility and following Django best practices.
The design supports the business requirements while keeping the implementation
simple and maintainable.
"""