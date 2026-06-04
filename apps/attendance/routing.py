"""WebSocket URL routing for attendance real-time updates."""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Lecturer monitors a session live
    re_path(
        r'ws/attendance/session/(?P<session_id>[A-Z0-9\-]+)/$',
        consumers.AttendanceSessionConsumer.as_asgi(),
    ),
    # Student receives confirmation after QR scan
    re_path(
        r'ws/attendance/student/$',
        consumers.StudentAttendanceConsumer.as_asgi(),
    ),
]
