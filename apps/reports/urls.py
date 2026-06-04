from django.urls import path
from . import views
urlpatterns = [
    path('course/<int:course_id>/', views.course_report_data),
    path('course/<int:course_id>/pdf/', views.export_pdf),
    path('course/<int:course_id>/excel/', views.export_excel),
]
