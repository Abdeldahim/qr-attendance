"""
Attendance app models.

Tables:
- AttendanceSession  — one per class meeting (QR code generation event)
- AttendanceRecord   — one per student per session (present / absent / late)

Security features enforced at model level:
- Unique constraint prevents duplicate attendance per session
- Session validity tracked via is_active + expiry timestamps
"""

import uuid
import secrets
from django.db import models
from django.utils import timezone
from django.conf import settings
from apps.courses.models import Course, Student, Lecturer


class AttendanceSession(models.Model):
    """
    Represents one attendance-taking event for a course.

    The lecturer starts a session → system generates a QR code.
    Students scan the QR → attendance records created.
    Lecturer ends session → session closed.
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    # Identity
    session_id = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        db_index=True,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='attendance_sessions',
    )
    lecturer = models.ForeignKey(
        Lecturer,
        on_delete=models.CASCADE,
        related_name='conducted_sessions',
    )

    # QR Code
    qr_token = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    qr_expiry_seconds = models.IntegerField(default=60)
    qr_generated_at = models.DateTimeField(null=True, blank=True)
    qr_image_path = models.CharField(max_length=500, blank=True)

    # Session lifecycle
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    # Counts (denormalised for fast dashboard queries)
    total_enrolled = models.IntegerField(default=0)
    total_present = models.IntegerField(default=0)

    # Optional: room info
    room = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'attendance_sessions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['course', 'status']),
            models.Index(fields=['lecturer', 'status']),
        ]

    def __str__(self):
        return f'{self.session_id} — {self.course.code} ({self.status})'

    def save(self, *args, **kwargs):
        if not self.session_id:
            self.session_id = self._generate_session_id()
        super().save(*args, **kwargs)

    def _generate_session_id(self):
        """Generate a readable session ID like NET2026-001."""
        course_code = self.course.code.replace('-', '').replace(' ', '')[:6].upper()
        year = timezone.now().year
        random_part = secrets.token_hex(2).upper()
        return f'{course_code}{year}-{random_part}'

    @property
    def is_qr_valid(self):
        """Return True if the current QR token is still within its expiry window."""
        if not self.qr_generated_at:
            return False
        if self.status != self.Status.ACTIVE:
            return False
        elapsed = (timezone.now() - self.qr_generated_at).total_seconds()
        return elapsed < self.qr_expiry_seconds

    @property
    def qr_seconds_remaining(self):
        """Seconds until the current QR code expires (0 if already expired)."""
        if not self.qr_generated_at:
            return 0
        elapsed = (timezone.now() - self.qr_generated_at).total_seconds()
        remaining = self.qr_expiry_seconds - elapsed
        return max(0, int(remaining))

    def refresh_qr_token(self):
        """Generate a new QR token (rotates the QR code)."""
        self.qr_token = uuid.uuid4()
        self.qr_generated_at = timezone.now()
        self.save(update_fields=['qr_token', 'qr_generated_at'])

    def complete_session(self):
        """End the attendance session."""
        self.status = self.Status.COMPLETED
        self.ended_at = timezone.now()
        self.is_completed = True
        # Refresh counts
        self.total_present = self.records.filter(
            status=AttendanceRecord.Status.PRESENT
        ).count()
        self.save()


class AttendanceRecord(models.Model):
    """
    One attendance record per student per session.

    UNIQUE constraint on (session, student) prevents duplicate attendance.
    """

    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'
        EXCUSED = 'EXCUSED', 'Excused'

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name='records',
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_records',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='attendance_records',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT,
        db_index=True,
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    # IP address at time of scan (for audit / fraud detection)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    # Device info
    device_info = models.CharField(max_length=500, blank=True)
    # Manual override by lecturer
    is_manual = models.BooleanField(default=False)
    modified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='modified_records',
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'attendance_records'
        # Critical: prevent a student from marking attendance twice in same session
        unique_together = ('session', 'student')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['student', 'course']),
            models.Index(fields=['session', 'status']),
        ]

    def __str__(self):
        return (
            f'{self.student.student_id} | {self.course.code} | '
            f'{self.session.session_id} | {self.status}'
        )
