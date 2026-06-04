from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.middleware.csrf import get_token
from django.contrib.auth import logout as auth_logout


@never_cache
def login_page(request):
    # If already logged in, go straight to dashboard
    if request.user.is_authenticated:
        role = request.user.role
        if role == 'ADMIN':
            return redirect('/dashboard/admin/')
        elif role == 'LECTURER':
            return redirect('/dashboard/lecturer/')
        else:
            return redirect('/dashboard/student/')

    get_token(request)  # force CSRF cookie
    next_url = request.GET.get('next', '')
    show_warning = bool(next_url and next_url not in ['/', ''])
    return render(request, 'accounts/login.html', {
        'next': next_url,
        'show_warning': show_warning,
    })


def logout_page(request):
    auth_logout(request)
    return redirect('/accounts/login/')
