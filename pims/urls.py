# pims/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # App URLs
    path('users/', include('users.urls')),
    path('devices/', include('devices.urls')),
    path('locations/', include('locations.urls')),
    path('vendors/', include('vendors.urls')),
    path('assignments/', include('assignments.urls')),
    path('maintenance/', include('maintenance.urls')),
    
    # Home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # Dashboard
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

# Custom error handlers
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'