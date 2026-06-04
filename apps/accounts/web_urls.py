from django.urls import path
from . import web_views

urlpatterns = [
    path('login/', web_views.login_page, name='login'),
    path('logout/', web_views.logout_page, name='logout'),
]
