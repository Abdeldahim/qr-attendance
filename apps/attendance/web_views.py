from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import AttendanceSession


@login_required(login_url='/accounts/login/')
def session_page(request, session_id):
    if not request.user.is_lecturer:
        return redirect('/dashboard/')
    try:
        lecturer = request.user.lecturer_profile
        session = AttendanceSession.objects.select_related(
            'course', 'lecturer__user'
        ).get(session_id=session_id, lecturer=lecturer)
    except Exception:
        return redirect('/dashboard/lecturer/')
    return render(request, 'attendance/session.html', {'session': session})


@login_required(login_url='/accounts/login/')
def scan_page(request, token=None):
    if not request.user.is_student:
        return redirect('/dashboard/')
    token = token or request.GET.get('token', '')
    return render(request, 'attendance/scan.html', {'token': token})
