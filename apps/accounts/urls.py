from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='api-login'),
    path('logout/', views.logout_view, name='api-logout'),
    path('token/refresh/', views.token_refresh_view, name='api-token-refresh'),
    path('me/', views.me_view, name='api-me'),
]
