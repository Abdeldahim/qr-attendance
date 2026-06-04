"""
Core app models.

AuditLog — records all significant system events:
- Login / logout
- Attendance marking
- QR code generation
- Admin actions
"""

from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """Immutable audit trail for all system events."""

    class EventType(models.TextChoices):
        # Auth
        LOGIN = 'LOGIN', 'User Login'
        LOGOUT = 'LOGOUT', 'User Logout'
        LOGIN_FAILED = 'LOGIN_FAILED', 'Failed Login Attempt'
        PASSWORD_CHANGED = 'PASSWORD_CHANGED', 'Password Changed'
        # Attendance
        ATTENDANCE_MARKED = 'ATTENDANCE_MARKED', 'Attendance Marked'
        ATTENDANCE_REJECTED = 'ATTENDANCE_REJECTED', 'Attendance Rejected'
        ATTENDANCE_MODIFIED = 'ATTENDANCE_MODIFIED', 'Attendance Modified'
        SESSION_STARTED = 'SESSION_STARTED', 'Session Started'
        SESSION_ENDED = 'SESSION_ENDED', 'Session Ended'
        QR_GENERATED = 'QR_GENERATED', 'QR Code Generated'
        # Admin
        USER_CREATED = 'USER_CREATED', 'User Created'
        USER_MODIFIED = 'USER_MODIFIED', 'User Modified'
        USER_DEACTIVATED = 'USER_DEACTIVATED', 'User Deactivated'
        COURSE_CREATED = 'COURSE_CREATED', 'Course Created'
        ENROLLMENT_CREATED = 'ENROLLMENT_CREATED', 'Student Enrolled'
        # System
        EXPORT_GENERATED = 'EXPORT_GENERATED', 'Report Exported'

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices, db_index=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    # Generic FK to relate to any object
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    extra_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['event_type', 'created_at']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f'[{self.event_type}] {user_str} — {self.created_at:%Y-%m-%d %H:%M}'

    @classmethod
    def log(cls, event_type, description, user=None, request=None,
            object_type='', object_id='', extra_data=None):
        """Convenience method to create an audit log entry."""
        ip_address = None
        user_agent = ''
        if request:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded:
                ip_address = x_forwarded.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        cls.objects.create(
            user=user,
            event_type=event_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            object_type=object_type,
            object_id=str(object_id),
            extra_data=extra_data,
        )
