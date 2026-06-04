from django.contrib import admin
from .models import Department, AcademicYear, Semester, Lecturer, Student, Course, Enrollment


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    search_fields = ['code', 'name']


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_current']


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'start_date', 'end_date', 'is_current']
    list_filter = ['academic_year', 'number', 'is_current']


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ['employee_id', '__str__', 'department', 'is_active']
    list_filter = ['department', 'is_active']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', '__str__', 'department', 'year_of_study', 'is_active']
    list_filter = ['department', 'year_of_study', 'is_active']
    search_fields = ['student_id', 'user__first_name', 'user__last_name']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'credit_hours', 'is_active']
    list_filter = ['department', 'semester', 'is_active']
    search_fields = ['code', 'name']
    filter_horizontal = ['lecturers']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'semester', 'enrolled_at', 'is_active']
    list_filter = ['course', 'semester', 'is_active']
    search_fields = ['student__student_id', 'student__user__last_name']
