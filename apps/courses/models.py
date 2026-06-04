"""
Courses app models.

Tables: Department, AcademicYear, Semester, Course, Lecturer, Student, Enrollment
All fields use standard Django types — fully compatible with SQLite and MySQL.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User


class Department(models.Model):
    """Faculty / Department — e.g. Faculty of Information Technology."""

    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='headed_departments',
        limit_choices_to={'role': User.Role.LECTURER},
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments'
        ordering = ['name']

    def __str__(self):
        return f'{self.code} — {self.name}'


class AcademicYear(models.Model):
    """Academic year — e.g. 2024/2025."""

    name = models.CharField(max_length=20, unique=True)   # e.g. "2024/2025"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = 'academic_years'
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_current:
            # Only one academic year is current at a time
            AcademicYear.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Semester(models.Model):
    """Semester within an academic year — e.g. Semester 1, 2024/2025."""

    class SemesterNumber(models.IntegerChoices):
        FIRST = 1, 'Semester 1'
        SECOND = 2, 'Semester 2'
        SUMMER = 3, 'Summer'

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='semesters',
    )
    number = models.IntegerField(choices=SemesterNumber.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = 'semesters'
        unique_together = ('academic_year', 'number')
        ordering = ['academic_year', 'number']

    def __str__(self):
        return f'{self.get_number_display()} — {self.academic_year}'

    def save(self, *args, **kwargs):
        if self.is_current:
            Semester.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Lecturer(models.Model):
    """Lecturer profile — linked to a User with role=LECTURER."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='lecturer_profile',
        limit_choices_to={'role': User.Role.LECTURER},
    )
    employee_id = models.CharField(max_length=30, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lecturers',
    )
    title = models.CharField(
        max_length=20,
        choices=[
            ('Dr.', 'Dr.'),
            ('Prof.', 'Prof.'),
            ('Mr.', 'Mr.'),
            ('Mrs.', 'Mrs.'),
            ('Ms.', 'Ms.'),
        ],
        default='Mr.',
    )
    specialization = models.CharField(max_length=200, blank=True)
    office_location = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lecturers'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f'{self.title} {self.user.get_full_name()} ({self.employee_id})'


class Student(models.Model):
    """Student profile — linked to a User with role=STUDENT."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        limit_choices_to={'role': User.Role.STUDENT},
    )
    student_id = models.CharField(max_length=30, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name='students',
    )
    year_of_study = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        default=1,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'students'
        ordering = ['student_id']

    def __str__(self):
        return f'{self.student_id} — {self.user.get_full_name()}'


class Course(models.Model):
    """A university course that has attendance sessions."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='courses',
    )
    credit_hours = models.IntegerField(default=3, validators=[MinValueValidator(1)])
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
    )
    # Many-to-many: a course can have multiple lecturers
    lecturers = models.ManyToManyField(
        Lecturer,
        related_name='courses',
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'

    def get_enrolled_students(self):
        return Student.objects.filter(
            enrollments__course=self,
            enrollments__is_active=True,
        )

    def get_total_sessions(self):
        return self.attendance_sessions.filter(is_completed=True).count()


class Enrollment(models.Model):
    """Links a student to a course for a given semester."""

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        null=True,
        related_name='enrollments',
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'enrollments'
        unique_together = ('student', 'course', 'semester')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f'{self.student.student_id} → {self.course.code}'
