from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from apps.core.models import AuditLog
from .models import User


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response({'error': 'Please enter both username and password.'}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response({'error': 'Invalid username or password.'}, status=401)

    if not user.is_active:
        return Response({'error': 'Your account has been deactivated.'}, status=403)

    # Log in using Django session — this is what makes @login_required work
    login(request, user)

    next_url = request.data.get('next', '').strip()
    if not next_url or not next_url.startswith('/'):
        next_url = _get_dashboard_url(user.role)

    try:
        AuditLog.log(AuditLog.EventType.LOGIN, f'{user.get_full_name()} logged in',
                     user=user, request=request)
    except Exception:
        pass

    return Response({
        'message': 'Login successful.',
        'user': {
            'id': user.pk,
            'username': user.username,
            'full_name': user.get_full_name(),
            'role': user.role,
        },
        'redirect': next_url,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    try:
        AuditLog.log(AuditLog.EventType.LOGOUT, f'{request.user.get_full_name()} logged out',
                     user=request.user if request.user.is_authenticated else None,
                     request=request)
    except Exception:
        pass
    logout(request)
    return Response({'message': 'Logged out successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    data = {
        'id': user.pk, 'username': user.username, 'email': user.email,
        'full_name': user.get_full_name(), 'role': user.role,
        'is_active': user.is_active,
    }
    if user.is_lecturer:
        try:
            lec = user.lecturer_profile
            data['lecturer'] = {
                'employee_id': lec.employee_id, 'title': lec.title,
                'department': lec.department.name if lec.department else None,
            }
        except Exception:
            pass
    if user.is_student:
        try:
            stu = user.student_profile
            data['student'] = {
                'student_id': stu.student_id,
                'department': stu.department.name if stu.department else None,
            }
        except Exception:
            pass
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh_view(request):
    return Response({'message': 'OK'})


def _get_dashboard_url(role):
    return {
        User.Role.ADMIN: '/dashboard/admin/',
        User.Role.LECTURER: '/dashboard/lecturer/',
        User.Role.STUDENT: '/dashboard/student/',
    }.get(role, '/dashboard/')
