from django.urls import path
from . import views

urlpatterns = [
    path('sessions/start/', views.start_session),
    path('sessions/<str:session_id>/end/', views.end_session),
    path('sessions/<str:session_id>/refresh-qr/', views.refresh_qr),
    path('sessions/<str:session_id>/status/', views.session_status),
    path('sessions/<str:session_id>/records/', views.session_records),
    path('scan/', views.scan_qr),
    path('my-records/', views.my_attendance_records),
    path('my-courses/', views.my_courses),
]
