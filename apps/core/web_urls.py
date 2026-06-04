from django.urls import path
from . import web_views

app_name = 'dashboard'

urlpatterns = [
    path('', web_views.dashboard_router, name='home'),
    path('admin/', web_views.admin_dashboard, name='admin'),
    path('lecturer/', web_views.lecturer_dashboard, name='lecturer'),
    path('student/', web_views.student_dashboard, name='student'),
]
