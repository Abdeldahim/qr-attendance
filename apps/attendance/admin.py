from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id', 'course', 'lecturer', 'status',
        'total_enrolled', 'total_present', 'started_at',
    ]
    list_filter = ['status', 'course__department']
    search_fields = ['session_id', 'course__code', 'course__name']
    readonly_fields = ['session_id', 'qr_token', 'started_at']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'session', 'status', 'recorded_at', 'is_manual']
    list_filter = ['status', 'is_manual', 'course']
    search_fields = ['student__student_id', 'student__user__last_name']
    readonly_fields = ['recorded_at']
