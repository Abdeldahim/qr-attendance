# University QR Attendance Management System

## Tech Stack
- **Backend**: Django 4.2 + Django REST Framework
- **Auth**: JWT via `djangorestframework-simplejwt`
- **Database**: SQLite (dev) → MySQL (production, zero code change)
- **Real-time**: Django Channels + WebSockets
- **QR Codes**: `qrcode` library
- **Reports**: `reportlab` (PDF) + `openpyxl` (Excel)
- **Frontend**: HTML5, CSS3, Vanilla JS

---

## Build Phases

| Phase | Description |
|-------|-------------|
| Phase 1 | Project setup, models, admin — **YOU ARE HERE** |
| Phase 2 | JWT Auth API + login UI |
| Phase 3 | QR code generation + lecturer dashboard |
| Phase 4 | Student scan + attendance recording |
| Phase 5 | Real-time WebSocket updates |
| Phase 6 | PDF + Excel reports |
| Phase 7 | Complete polished UI |

---

## Phase 1 Setup Instructions

### Prerequisites
- Python 3.10+
- pip

### Step 1 — Install dependencies

```bash
pip install django==4.2 djangorestframework==3.14 \
    djangorestframework-simplejwt==5.3 \
    django-cors-headers==4.3 \
    qrcode[pil]==7.4 \
    Pillow==10.2 \
    reportlab==4.1 \
    openpyxl==3.1 \
    django-filter==23.5 \
    channels==4.0 \
    daphne==4.0
```

### Step 2 — Navigate to project

```bash
cd qr_attendance
```

### Step 3 — Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 4 — Seed initial data

```bash
python manage.py seed_data
```

This creates:
- Admin account: `admin` / `admin123`
- 3 sample departments
- 6 sample courses
- 3 sample lecturers
- 10 sample students

### Step 5 — Run the development server

```bash
python manage.py runserver
```

### Step 6 — Test Phase 1

Visit: http://127.0.0.1:8000/admin/

Login: `admin` / `admin123`

You should see all models in the Django admin panel:
- Users, Students, Lecturers
- Departments, Courses, Enrollments
- Attendance Sessions, Attendance Records
- Audit Logs

---

## Switching to MySQL (Production)

In `settings.py`, change the `DATABASES` setting:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'university_attendance',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}
```

Install MySQL driver:
```bash
pip install mysqlclient
```

Then run:
```bash
python manage.py migrate
python manage.py seed_data
```

**Zero application logic changes required.**
