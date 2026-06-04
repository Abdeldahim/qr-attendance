from django.urls import path
from . import web_views

urlpatterns = [
    path('session/<str:session_id>/', web_views.session_page, name='session'),
    path('scan/', web_views.scan_page, name='scan'),
    path('scan/<str:token>/', web_views.scan_page, name='scan-token'),
]
