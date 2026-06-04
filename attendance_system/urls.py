"""Main URL configuration for University QR Attendance System."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/auth/', include('apps.accounts.urls')),
    path('api/courses/', include('apps.courses.urls')),
    path('api/attendance/', include('apps.attendance.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/core/', include('apps.core.urls')),

    # Web UI (template-based)
    path('accounts/', include('apps.accounts.web_urls')),
    path('dashboard/', include('apps.core.web_urls')),
    path('courses/', include('apps.courses.web_urls')),
    path('attendance/', include('apps.attendance.web_urls')),
    path('reports/', include('apps.reports.web_urls')),

    # Root redirect
    path('', lambda request: redirect('dashboard:home'), name='root'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
