from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q


def dashboard_router(request):
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')
    if request.user.role == 'ADMIN':
        return redirect('/dashboard/admin/')
    elif request.user.role == 'LECTURER':
        return redirect('/dashboard/lecturer/')
    else:
        return redirect('/dashboard/student/')


@login_required(login_url='/accounts/login/')
def admin_dashboard(request):
    if request.user.role != 'ADMIN':
        return redirect('/dashboard/')

    from apps.courses.models import Department, Course, Student, Lecturer
    from apps.attendance.models import AttendanceSession

    context = {
        'total_students': Student.objects.filter(is_active=True).count(),
        'total_lecturers': Lecturer.objects.filter(is_active=True).count(),
        'total_courses': Course.objects.filter(is_active=True).count(),
        'total_departments': Department.objects.filter(is_active=True).count(),
        'active_sessions': AttendanceSession.objects.filter(status='ACTIVE').count(),
        'recent_sessions': AttendanceSession.objects.select_related(
            'course', 'lecturer__user'
        ).order_by('-started_at')[:10],
        'departments': Department.objects.annotate(
            course_count=Count('courses', filter=Q(courses__is_active=True)),
            student_count=Count('students', filter=Q(students__is_active=True)),
        ).filter(is_active=True),
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required(login_url='/accounts/login/')
def lecturer_dashboard(request):
    if request.user.role != 'LECTURER':
        return redirect('/dashboard/')

    try:
        lecturer = request.user.lecturer_profile
    except Exception:
        return render(request, 'dashboard/error.html',
                      {'message': 'Lecturer profile not found.'})

    from apps.courses.models import Course
    from apps.attendance.models import AttendanceSession

    courses = Course.objects.filter(
        lecturers=lecturer, is_active=True
    ).annotate(
        enrolled_count=Count('enrollments', filter=Q(enrollments__is_active=True)),
        session_count=Count('attendance_sessions',
                            filter=Q(attendance_sessions__is_completed=True)),
    )

    active_sessions = AttendanceSession.objects.filter(
        lecturer=lecturer, status='ACTIVE'
    ).select_related('course')

    recent_sessions = AttendanceSession.objects.filter(
        lecturer=lecturer
    ).select_related('course').order_by('-started_at')[:8]

    context = {
        'lecturer': lecturer,
        'courses': courses,
        'active_sessions': active_sessions,
        'recent_sessions': recent_sessions,
        'total_courses': courses.count(),
        'total_sessions': AttendanceSession.objects.filter(
            lecturer=lecturer, is_completed=True
        ).count(),
    }
    return render(request, 'dashboard/lecturer_dashboard.html', context)


@login_required(login_url='/accounts/login/')
def student_dashboard(request):
    if request.user.role != 'STUDENT':
        return redirect('/dashboard/')

    try:
        student = request.user.student_profile
    except Exception:
        return render(request, 'dashboard/error.html',
                      {'message': 'Student profile not found.'})

    from apps.courses.models import Enrollment
    from apps.attendance.models import AttendanceRecord, AttendanceSession

    enrollments = Enrollment.objects.filter(
        student=student, is_active=True
    ).select_related('course', 'course__department')

    course_stats = []
    for enrollment in enrollments:
        course = enrollment.course
        total_sessions = AttendanceSession.objects.filter(
            course=course, is_completed=True
        ).count()
        attended = AttendanceRecord.objects.filter(
            student=student, course=course, status='PRESENT'
        ).count()
        pct = round((attended / total_sessions * 100) if total_sessions > 0 else 0, 1)
        course_stats.append({
            'course': course,
            'total_sessions': total_sessions,
            'attended': attended,
            'percentage': pct,
            'status': 'good' if pct >= 75 else ('warning' if pct >= 60 else 'danger'),
        })

    recent_records = AttendanceRecord.objects.filter(
        student=student
    ).select_related('course', 'session').order_by('-recorded_at')[:10]

    overall_sessions = sum(s['total_sessions'] for s in course_stats)
    overall_attended = sum(s['attended'] for s in course_stats)
    overall_pct = round(
        (overall_attended / overall_sessions * 100) if overall_sessions > 0 else 0, 1
    )

    context = {
        'student': student,
        'course_stats': course_stats,
        'recent_records': recent_records,
        'overall_pct': overall_pct,
        'overall_sessions': overall_sessions,
        'overall_attended': overall_attended,
        'total_courses': enrollments.count(),
    }
    return render(request, 'dashboard/student_dashboard.html', context)
