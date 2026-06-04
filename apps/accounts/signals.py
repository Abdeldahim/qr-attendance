"""
Signals for the accounts app.
Automatically creates audit log entries on user login/logout.
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from apps.core.models import AuditLog


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    user.last_login_ip = _get_ip(request)
    user.save(update_fields=['last_login_ip'])
    AuditLog.log(
        event_type=AuditLog.EventType.LOGIN,
        description=f'{user.get_full_name()} logged in',
        user=user,
        request=request,
    )


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user:
        AuditLog.log(
            event_type=AuditLog.EventType.LOGOUT,
            description=f'{user.get_full_name()} logged out',
            user=user,
            request=request,
        )


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    AuditLog.log(
        event_type=AuditLog.EventType.LOGIN_FAILED,
        description=f'Failed login attempt for username: {credentials.get("username", "?")}',
        request=request,
    )


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
