"""
Attendance API views.

POST /api/attendance/sessions/start/          — Lecturer starts a session
POST /api/attendance/sessions/<id>/end/       — Lecturer ends a session
POST /api/attendance/sessions/<id>/refresh-qr/ — Rotate QR token
GET  /api/attendance/sessions/<id>/status/    — Get live counts
POST /api/attendance/scan/                    — Student scans QR code
GET  /api/attendance/my-records/              — Student's own records
GET  /api/attendance/sessions/<id>/records/   — Lecturer views session records
"""

import io
import base64
import qrcode
from django.conf import settings
from django.utils import timezone
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.courses.models import Course, Enrollment
from apps.core.models import AuditLog
from .models import AttendanceSession, AttendanceRecord


def _require_lecturer(request):
    if not request.user.is_lecturer:
        return Response({'error': 'Lecturer access required.'}, status=403)
    try:
        return request.user.lecturer_profile
    except Exception:
        return Response({'error': 'Lecturer profile not found.'}, status=403)


def _generate_qr_b64(token, course_id, session_id):
    """Generate QR code and return as base64-encoded PNG string."""
    payload = f"UNIATTEND|{token}|{course_id}|{session_id}|{int(timezone.now().timestamp())}"
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0A4D68", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_session(request):
    """Lecturer starts an attendance session for a course."""
    result = _require_lecturer(request)
    if isinstance(result, Response):
        return result
    lecturer = result

    course_id = request.data.get('course_id')
    room = request.data.get('room', '')
    notes = request.data.get('notes', '')
    expiry = int(request.data.get('qr_expiry_seconds', settings.QR_CODE_DEFAULT_EXPIRY))
    expiry = max(settings.QR_CODE_MIN_EXPIRY, min(settings.QR_CODE_MAX_EXPIRY, expiry))

    try:
        course = Course.objects.get(pk=course_id, lecturers=lecturer, is_active=True)
    except Course.DoesNotExist:
        return Response({'error': 'Course not found or not assigned to you.'}, status=404)

    # Check no active session already running for this course
    existing = AttendanceSession.objects.filter(course=course, status='ACTIVE').first()
    if existing:
        return Response({
            'error': 'An active session already exists for this course.',
            'session_id': existing.session_id,
        }, status=409)

    enrolled_count = Enrollment.objects.filter(course=course, is_active=True).count()

    session = AttendanceSession.objects.create(
        course=course,
        lecturer=lecturer,
        qr_expiry_seconds=expiry,
        qr_generated_at=timezone.now(),
        total_enrolled=enrolled_count,
        room=room,
        notes=notes,
    )

    qr_b64 = _generate_qr_b64(str(session.qr_token), course.pk, session.session_id)

    AuditLog.log(
        AuditLog.EventType.SESSION_STARTED,
        f'Session {session.session_id} started for {course.code}',
        user=request.user, request=request,
        object_type='AttendanceSession', object_id=session.pk,
    )

    return Response({
        'session_id': session.session_id,
        'course': {'id': course.pk, 'code': course.code, 'name': course.name},
        'qr_token': str(session.qr_token),
        'qr_image_b64': qr_b64,
        'qr_expiry_seconds': session.qr_expiry_seconds,
        'qr_seconds_remaining': session.qr_seconds_remaining,
        'total_enrolled': enrolled_count,
        'total_present': 0,
        'status': session.status,
        'started_at': session.started_at.isoformat(),
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_session(request, session_id):
    """Lecturer ends a session."""
    result = _require_lecturer(request)
    if isinstance(result, Response):
        return result
    lecturer = result

    try:
        session = AttendanceSession.objects.get(session_id=session_id, lecturer=lecturer)
    except AttendanceSession.DoesNotExist:
        return Response({'error': 'Session not found.'}, status=404)

    if session.status != 'ACTIVE':
        return Response({'error': 'Session is not active.'}, status=400)

    session.complete_session()

    # Mark absent students
    enrolled_ids = set(
        Enrollment.objects.filter(course=session.course, is_active=True)
        .values_list('student_id', flat=True)
    )
    present_ids = set(
        session.records.filter(status='PRESENT').values_list('student_id', flat=True)
    )
    absent_ids = enrolled_ids - present_ids

    absent_records = [
        AttendanceRecord(
            session=session,
            student_id=sid,
            course=session.course,
            status='ABSENT',
            is_manual=True,
        )
        for sid in absent_ids
    ]
    AttendanceRecord.objects.bulk_create(absent_records, ignore_conflicts=True)

    AuditLog.log(
        AuditLog.EventType.SESSION_ENDED,
        f'Session {session.session_id} ended — {session.total_present} present',
        user=request.user, request=request,
        object_type='AttendanceSession', object_id=session.pk,
    )

    return Response({
        'message': 'Session ended successfully.',
        'session_id': session.session_id,
        'total_present': session.total_present,
        'total_absent': len(absent_ids),
        'total_enrolled': session.total_enrolled,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_qr(request, session_id):
    """Rotate the QR token — generates a new QR image."""
    result = _require_lecturer(request)
    if isinstance(result, Response):
        return result
    lecturer = result

    try:
        session = AttendanceSession.objects.get(session_id=session_id, lecturer=lecturer, status='ACTIVE')
    except AttendanceSession.DoesNotExist:
        return Response({'error': 'Active session not found.'}, status=404)

    session.refresh_qr_token()
    qr_b64 = _generate_qr_b64(str(session.qr_token), session.course.pk, session.session_id)

    AuditLog.log(
        AuditLog.EventType.QR_GENERATED,
        f'QR refreshed for session {session.session_id}',
        user=request.user, request=request,
    )

    # Broadcast new QR to WebSocket group
    _broadcast_qr_refresh(session, qr_b64)

    return Response({
        'qr_token': str(session.qr_token),
        'qr_image_b64': qr_b64,
        'qr_expiry_seconds': session.qr_expiry_seconds,
        'qr_seconds_remaining': session.qr_seconds_remaining,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_status(request, session_id):
    """Return live attendance counts for a session."""
    try:
        session = AttendanceSession.objects.get(session_id=session_id)
    except AttendanceSession.DoesNotExist:
        return Response({'error': 'Session not found.'}, status=404)

    # Access control
    if request.user.is_lecturer:
        try:
            if session.lecturer != request.user.lecturer_profile:
                return Response({'error': 'Access denied.'}, status=403)
        except Exception:
            return Response({'error': 'Access denied.'}, status=403)

    present = session.records.filter(status='PRESENT').count()
    absent_count = session.total_enrolled - present

    recent_attendees = session.records.filter(
        status='PRESENT'
    ).select_related('student__user').order_by('-recorded_at')[:20]

    return Response({
        'session_id': session.session_id,
        'status': session.status,
        'total_enrolled': session.total_enrolled,
        'total_present': present,
        'total_absent': max(0, absent_count),
        'qr_seconds_remaining': session.qr_seconds_remaining,
        'is_qr_valid': session.is_qr_valid,
        'recent_attendees': [
            {
                'student_id': r.student.student_id,
                'name': r.student.user.get_full_name(),
                'recorded_at': r.recorded_at.isoformat(),
            }
            for r in recent_attendees
        ],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scan_qr(request):
    """
    Student scans a QR code.

    Validates:
    1. Student role
    2. QR token → active session
    3. Session still active
    4. QR not expired
    5. Student enrolled in course
    6. Not already marked present

    On success: creates AttendanceRecord, pushes WebSocket update.
    """
    if not request.user.is_student:
        return Response({'error': 'Student access required.'}, status=403)

    try:
        student = request.user.student_profile
    except Exception:
        return Response({'error': 'Student profile not found.'}, status=403)

    # Parse QR payload: "UNIATTEND|<token>|<course_id>|<session_id>|<ts>"
    qr_payload = request.data.get('qr_payload', '')
    qr_token = request.data.get('qr_token', '')  # Also accept token directly

    if qr_payload:
        try:
            parts = qr_payload.split('|')
            if parts[0] != 'UNIATTEND' or len(parts) < 4:
                raise ValueError('Bad format')
            qr_token = parts[1]
        except Exception:
            return Response({'error': 'Invalid QR code format.'}, status=400)

    if not qr_token:
        return Response({'error': 'QR token is required.'}, status=400)

    # Find session by token
    try:
        session = AttendanceSession.objects.select_related('course').get(
            qr_token=qr_token
        )
    except AttendanceSession.DoesNotExist:
        AuditLog.log(
            AuditLog.EventType.ATTENDANCE_REJECTED,
            f'Student {student.student_id} used invalid QR token',
            user=request.user, request=request,
        )
        return Response({'error': 'QR code is invalid or has expired.'}, status=400)

    # Session must be active
    if session.status != 'ACTIVE':
        return Response({'error': 'This attendance session has ended.'}, status=400)

    # QR must not be expired
    if not session.is_qr_valid:
        return Response({
            'error': 'QR code has expired. Ask your lecturer to refresh it.',
            'code': 'QR_EXPIRED',
        }, status=400)

    course = session.course

    # Student must be enrolled
    enrolled = Enrollment.objects.filter(
        student=student, course=course, is_active=True
    ).exists()
    if not enrolled:
        AuditLog.log(
            AuditLog.EventType.ATTENDANCE_REJECTED,
            f'Student {student.student_id} not enrolled in {course.code}',
            user=request.user, request=request,
        )
        return Response({
            'error': f'You are not enrolled in {course.name}.',
            'code': 'NOT_ENROLLED',
        }, status=403)

    # Create attendance record (unique_together prevents duplicates)
    try:
        record = AttendanceRecord.objects.create(
            session=session,
            student=student,
            course=course,
            status='PRESENT',
            ip_address=_get_ip(request),
            device_info=request.META.get('HTTP_USER_AGENT', '')[:200],
        )
    except IntegrityError:
        return Response({
            'error': 'Attendance already recorded for this session.',
            'code': 'ALREADY_MARKED',
        }, status=409)

    # Update denormalised count
    present_count = session.records.filter(status='PRESENT').count()
    session.total_present = present_count
    session.save(update_fields=['total_present'])

    AuditLog.log(
        AuditLog.EventType.ATTENDANCE_MARKED,
        f'Student {student.student_id} marked present in {course.code}',
        user=request.user, request=request,
        object_type='AttendanceRecord', object_id=record.pk,
    )

    # Push real-time update to lecturer's WebSocket group
    _broadcast_attendance(session, student, record, present_count)

    return Response({
        'message': f'Attendance recorded! You are marked present for {course.name}.',
        'course': course.name,
        'course_code': course.code,
        'session_id': session.session_id,
        'recorded_at': record.recorded_at.isoformat(),
        'status': 'PRESENT',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_attendance_records(request):
    """Student views their own attendance history."""
    if not request.user.is_student:
        return Response({'error': 'Student access required.'}, status=403)
    try:
        student = request.user.student_profile
    except Exception:
        return Response({'error': 'Profile not found.'}, status=403)

    course_id = request.query_params.get('course_id')
    qs = AttendanceRecord.objects.filter(student=student).select_related(
        'course', 'session'
    ).order_by('-recorded_at')
    if course_id:
        qs = qs.filter(course_id=course_id)

    return Response([
        {
            'id': r.pk,
            'course': r.course.name,
            'course_code': r.course.code,
            'session_id': r.session.session_id,
            'status': r.status,
            'recorded_at': r.recorded_at.isoformat(),
        }
        for r in qs[:100]
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_records(request, session_id):
    """Lecturer views all attendance records for a session."""
    result = _require_lecturer(request)
    if isinstance(result, Response):
        return result
    lecturer = result

    try:
        session = AttendanceSession.objects.get(session_id=session_id, lecturer=lecturer)
    except AttendanceSession.DoesNotExist:
        return Response({'error': 'Session not found.'}, status=404)

    records = session.records.select_related('student__user').order_by('student__student_id')

    return Response({
        'session_id': session.session_id,
        'course': session.course.name,
        'status': session.status,
        'total_enrolled': session.total_enrolled,
        'total_present': session.total_present,
        'records': [
            {
                'student_id': r.student.student_id,
                'name': r.student.user.get_full_name(),
                'status': r.status,
                'recorded_at': r.recorded_at.isoformat() if r.recorded_at else None,
                'is_manual': r.is_manual,
            }
            for r in records
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_courses(request):
    """Lecturer: list assigned courses with session stats."""
    result = _require_lecturer(request)
    if isinstance(result, Response):
        return result
    lecturer = result

    from django.db.models import Count, Q
    courses = Course.objects.filter(
        lecturers=lecturer, is_active=True
    ).annotate(
        enrolled_count=Count('enrollments', filter=Q(enrollments__is_active=True)),
        session_count=Count('attendance_sessions', filter=Q(attendance_sessions__is_completed=True)),
    )

    return Response([
        {
            'id': c.pk,
            'code': c.code,
            'name': c.name,
            'department': c.department.name,
            'enrolled_count': c.enrolled_count,
            'session_count': c.session_count,
            'active_session': _get_active_session(c, lecturer),
        }
        for c in courses
    ])


def _get_active_session(course, lecturer):
    session = AttendanceSession.objects.filter(
        course=course, lecturer=lecturer, status='ACTIVE'
    ).first()
    if session:
        return {'session_id': session.session_id, 'started_at': session.started_at.isoformat()}
    return None


def _get_ip(request):
    x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_fwd:
        return x_fwd.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _broadcast_attendance(session, student, record, present_count):
    """Push attendance update to lecturer's WebSocket channel group."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'session_{session.session_id}',
            {
                'type': 'attendance_update',
                'event': 'STUDENT_MARKED',
                'student_id': student.student_id,
                'student_name': student.user.get_full_name(),
                'recorded_at': record.recorded_at.isoformat(),
                'total_present': present_count,
                'total_enrolled': session.total_enrolled,
            }
        )
    except Exception:
        pass  # WebSocket is optional — don't break attendance if channels not available


def _broadcast_qr_refresh(session, qr_b64):
    """Push new QR code to lecturer's WebSocket group."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'session_{session.session_id}',
            {
                'type': 'attendance_update',
                'event': 'QR_REFRESHED',
                'qr_image_b64': qr_b64,
                'qr_token': str(session.qr_token),
                'qr_seconds_remaining': session.qr_seconds_remaining,
            }
        )
    except Exception:
        pass
