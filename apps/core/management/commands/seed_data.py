"""
Management command: seed_data

Populates the database with realistic demo data for testing Phase 1.

Usage:
    python manage.py seed_data

Creates:
    - 1 Admin account         (admin / admin123)
    - 3 Departments
    - 1 Academic Year + 2 Semesters
    - 3 Lecturers
    - 6 Courses
    - 10 Students
    - Enrollments (each student in 3–4 courses)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = 'Seed database with demo data for testing'

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.courses.models import (
            Department, AcademicYear, Semester,
            Lecturer, Student, Course, Enrollment,
        )

        self.stdout.write(self.style.HTTP_INFO('\n🌱 Seeding database...\n'))

        # ------------------------------------------------------------------
        # 1. Admin
        # ------------------------------------------------------------------
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@university.edu',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('  ✅ Admin created: admin / admin123'))
        else:
            self.stdout.write('  ⏩ Admin already exists')

        # ------------------------------------------------------------------
        # 2. Departments
        # ------------------------------------------------------------------
        dept_data = [
            ('FIT', 'Faculty of Information Technology'),
            ('FBE', 'Faculty of Business & Economics'),
            ('FEN', 'Faculty of Engineering'),
        ]
        departments = {}
        for code, name in dept_data:
            dept, created = Department.objects.get_or_create(
                code=code, defaults={'name': name}
            )
            departments[code] = dept
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Department: {name}'))

        # ------------------------------------------------------------------
        # 3. Academic Year + Semesters
        # ------------------------------------------------------------------
        acad_year, created = AcademicYear.objects.get_or_create(
            name='2025/2026',
            defaults={
                'start_date': date(2025, 9, 1),
                'end_date': date(2026, 6, 30),
                'is_current': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✅ Academic Year: 2025/2026'))

        sem1, _ = Semester.objects.get_or_create(
            academic_year=acad_year,
            number=1,
            defaults={
                'start_date': date(2025, 9, 1),
                'end_date': date(2026, 1, 31),
                'is_current': True,
            }
        )
        sem2, _ = Semester.objects.get_or_create(
            academic_year=acad_year,
            number=2,
            defaults={
                'start_date': date(2026, 2, 1),
                'end_date': date(2026, 6, 30),
            }
        )
        self.stdout.write(self.style.SUCCESS('  ✅ Semesters created'))

        # ------------------------------------------------------------------
        # 4. Lecturers
        # ------------------------------------------------------------------
        lecturer_data = [
            ('L001', 'Dr.', 'Alice', 'Mugisha', 'alice.mugisha@university.edu', 'FIT', 'Networking & Security'),
            ('L002', 'Prof.', 'Bernard', 'Habimana', 'b.habimana@university.edu', 'FBE', 'Finance & Accounting'),
            ('L003', 'Dr.', 'Claire', 'Uwimana', 'c.uwimana@university.edu', 'FEN', 'Software Engineering'),
        ]
        lecturers = {}
        for emp_id, title, first, last, email, dept_code, spec in lecturer_data:
            user, u_created = User.objects.get_or_create(
                username=emp_id.lower(),
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'role': User.Role.LECTURER,
                    'is_active': True,
                }
            )
            if u_created:
                user.set_password('lecturer123')
                user.save()

            lec, created = Lecturer.objects.get_or_create(
                employee_id=emp_id,
                defaults={
                    'user': user,
                    'department': departments[dept_code],
                    'title': title,
                    'specialization': spec,
                }
            )
            lecturers[emp_id] = lec
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Lecturer: {title} {first} {last} ({emp_id}) — password: lecturer123'
                ))

        # ------------------------------------------------------------------
        # 5. Courses
        # ------------------------------------------------------------------
        course_data = [
            ('CS101', 'Computer Networks', 'FIT', 3, 'L001'),
            ('CS102', 'Database Systems', 'FIT', 3, 'L001'),
            ('CS103', 'Operating Systems', 'FIT', 3, 'L003'),
            ('CS201', 'Software Engineering', 'FIT', 4, 'L003'),
            ('BA101', 'Financial Accounting', 'FBE', 3, 'L002'),
            ('BA102', 'Marketing Principles', 'FBE', 3, 'L002'),
        ]
        courses = {}
        for code, name, dept_code, credits, lec_id in course_data:
            course, created = Course.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'department': departments[dept_code],
                    'credit_hours': credits,
                    'semester': sem1,
                }
            )
            course.lecturers.add(lecturers[lec_id])
            courses[code] = course
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Course: {code} — {name}'))

        # ------------------------------------------------------------------
        # 6. Students
        # ------------------------------------------------------------------
        student_data = [
            ('STU001', 'Jean', 'Ndikumana', 'jean.ndikumana@student.edu', 'FIT', 1),
            ('STU002', 'Marie', 'Uwase', 'marie.uwase@student.edu', 'FIT', 1),
            ('STU003', 'Patrick', 'Nzabahimana', 'p.nzabahimana@student.edu', 'FIT', 2),
            ('STU004', 'Grace', 'Mukamana', 'grace.mukamana@student.edu', 'FIT', 2),
            ('STU005', 'Eric', 'Habimana', 'eric.habimana@student.edu', 'FBE', 1),
            ('STU006', 'Diane', 'Iradukunda', 'diane.irad@student.edu', 'FBE', 1),
            ('STU007', 'Kevin', 'Niyonkuru', 'kevin.n@student.edu', 'FIT', 3),
            ('STU008', 'Sandra', 'Kayitesi', 'sandra.k@student.edu', 'FEN', 1),
            ('STU009', 'Peter', 'Mugabo', 'peter.m@student.edu', 'FIT', 1),
            ('STU010', 'Anita', 'Nishimwe', 'anita.n@student.edu', 'FBE', 2),
        ]

        students = {}
        for s_id, first, last, email, dept_code, year in student_data:
            user, u_created = User.objects.get_or_create(
                username=s_id.lower(),
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'role': User.Role.STUDENT,
                    'is_active': True,
                }
            )
            if u_created:
                user.set_password('student123')
                user.save()

            stu, created = Student.objects.get_or_create(
                student_id=s_id,
                defaults={
                    'user': user,
                    'department': departments[dept_code],
                    'year_of_study': year,
                }
            )
            students[s_id] = stu
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Student: {first} {last} ({s_id}) — password: student123'
                ))

        # ------------------------------------------------------------------
        # 7. Enrollments
        # ------------------------------------------------------------------
        enrollment_map = {
            'STU001': ['CS101', 'CS102', 'CS103'],
            'STU002': ['CS101', 'CS102', 'CS201'],
            'STU003': ['CS101', 'CS103', 'CS201'],
            'STU004': ['CS102', 'CS103', 'CS201'],
            'STU005': ['BA101', 'BA102'],
            'STU006': ['BA101', 'BA102'],
            'STU007': ['CS101', 'CS102', 'CS103', 'CS201'],
            'STU008': ['CS103', 'CS201'],
            'STU009': ['CS101', 'CS102'],
            'STU010': ['BA101', 'BA102'],
        }

        enroll_count = 0
        for s_id, course_codes in enrollment_map.items():
            for c_code in course_codes:
                _, created = Enrollment.objects.get_or_create(
                    student=students[s_id],
                    course=courses[c_code],
                    semester=sem1,
                    defaults={'is_active': True}
                )
                if created:
                    enroll_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✅ {enroll_count} enrollments created'))

        # ------------------------------------------------------------------
        # Done
        # ------------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS('\n' + '='*55))
        self.stdout.write(self.style.SUCCESS('✅  Database seeded successfully!\n'))
        self.stdout.write(self.style.HTTP_INFO('🔐 Login credentials:\n'))
        self.stdout.write('   Admin    → username: admin      / password: admin123')
        self.stdout.write('   Lecturer → username: l001       / password: lecturer123')
        self.stdout.write('   Lecturer → username: l002       / password: lecturer123')
        self.stdout.write('   Lecturer → username: l003       / password: lecturer123')
        self.stdout.write('   Student  → username: stu001     / password: student123')
        self.stdout.write('             (stu002 … stu010 all use student123)')
        self.stdout.write(self.style.SUCCESS('='*55 + '\n'))
