

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    # User List and Management
    path('', views.UserListView.as_view(), name='list'),
    path('create/', views.UserCreateView.as_view(), name='create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='delete'),
    
    # Role and Permission Management
    path('<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='roles'),
    path('<int:pk>/permissions/', views.UserPermissionView.as_view(), name='permissions'),
    
    # User Profile Management
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/edit/', views.UserProfileEditView.as_view(), name='profile_edit'),
    path('profile/password/', views.UserPasswordChangeView.as_view(), name='password_change'),
    
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='logout'),
    
    # Password Reset URLs
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'),
    
    # User Search and Filtering
    path('search/', views.UserSearchView.as_view(), name='search'),
    
    # Employee ID Lookup (AJAX endpoint)
    path('lookup/<str:employee_id>/', views.user_lookup_by_employee_id, name='lookup'),
    
    # User Status Management
    path('<int:pk>/activate/', views.UserActivateView.as_view(), name='activate'),
    path('<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='deactivate'),
    
    # User Reports and Analytics
    path('reports/', views.UserReportsView.as_view(), name='reports'),
    path('export/', views.UserExportView.as_view(), name='export'),
]