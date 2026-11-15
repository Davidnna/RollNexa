# RollNexa

**Attendance, connected.**

RollNexa is a web-based Smart Academic Attendance Platform prototype. It connects institutional academic structures, course delivery, student registration, lecturer responsibilities and attendance-session management. Its selected attendance policy requires both QR Code verification and Facial Recognition to succeed before a student can be recorded as present.

## Current release: 0.6.0 — Attendance management foundation

Version 0.6.0 extends the existing RollNexa application with lecturer-managed attendance sessions and the server-side foundation for the agreed dual-verification workflow. It does not replace the existing authentication, academic, course-management or database architecture.

### Implemented functionality

- Django authentication and session management.
- System administrator, lecturer and student roles.
- Administrator-created student and lecturer accounts, temporary passwords and mandatory first-sign-in password changes.
- Account activation and deactivation, with role-specific dashboards.
- Faculty, department, programme, academic session and semester management.
- Administrator-only academic and course CSV import with validation, preview and atomic commit.
- Department-owned master course records and programme-specific course offerings.
- Programme-specific credit units, curriculum classifications and source provenance.
- Lecturer directory, lecturer profile management and departmental affiliation.
- Multiple lecturer assignments per course offering, including permitted cross-department teaching.
- Teaching-assignment revocation history and administrator audit details.
- Lecturer access restricted to actively assigned course offerings and class rosters.
- Student course registration and withdrawal, subject to offering rules.
- Lecturer attendance-session scheduling, activation, closure and cancellation.
- Attendance-session management restricted to lecturers with active teaching assignments.
- Attendance-session lifecycle timestamps and database integrity constraints.
- An attendance-record model with one record per student per session.
- A server-side attendance service that requires successful QR and facial verification outcomes, both timestamps, and QR verification before facial verification.
- Neon PostgreSQL persistence and deployment configuration for Render.

### Not yet implemented

Version 0.6.0 does not generate or scan QR Codes, enrol student faces, capture facial images, perform liveness detection, run a facial-recognition model, or expose a student check-in interface. Attendance analytics, absence calculation and report exports are also planned modules.

Activating an attendance session does not mark students present. The attendance-record service is an integration boundary for the future verification components. It must be called only by trusted server-side orchestration after both verification systems have independently succeeded. The service itself does not decode QR tokens or perform facial recognition.

## Agreed attendance verification policy

RollNexa uses **QR Code AND Facial Recognition**, not either method independently.

1. An authorised lecturer schedules and activates an attendance session for an assigned course offering.
2. A student must be eligible for the course offering and access the active session.
3. QR Code verification must succeed first.
4. Facial Recognition must then successfully verify the student's identity against an enrolled reference.
5. Both verification timestamps must fall within the active session window.
6. The server records attendance only when both checks succeed and all eligibility and integrity checks pass.

If either verification fails or is missing, no present record is created. QR Code generation, face enrolment, liveness detection and recognition will be implemented in later releases. No raw face image or biometric template is collected or stored by version 0.6.0.

## User roles and access

| Role | Main responsibilities |
| --- | --- |
| System administrator | Manage user accounts, institutional structure, academic sessions, semesters, course catalogue, course offerings and lecturer assignments; review imports and administrative records. |
| Lecturer | View assigned course offerings and registered student rosters; schedule, activate, close and cancel attendance sessions for assigned offerings. |
| Student | View eligible course offerings and manage course registration or withdrawal where registration rules permit. Student attendance check-in is not yet available in version 0.6.0. |

Permissions are enforced in Django views and services. Hiding a link in the interface is not treated as an access-control mechanism.

## Academic and course data model

- A `Faculty` contains departments.
- A `Department` belongs to one faculty and contains programmes.
- A `Programme` belongs to one department. Award and duration are optional when an official source does not confirm them.
- An `AcademicSession` contains semesters. At most one academic session and one semester can be current at a time; a current semester must belong to the current session.
- A student profile can reference a programme and current level. The student's department is derived from the programme's department.
- A lecturer profile can reference a department.
- A master `Course` is owned by a department and stores the shared course identity.
- A `CourseOffering` delivers a course to a specific programme, semester and level. The same master course can be offered to multiple programmes, with programme-specific credit units and curriculum classifications.
- A `CourseLecturerAssignment` links a lecturer to a course offering. Lecturer access requires an active assignment.
- A `CourseRegistration` links a student to a course offering and records registered or withdrawn status. Re-registration updates the existing registration row.
- An `AttendanceSession` belongs to one course offering and records its scheduled time window and lifecycle.
- An `AttendanceRecord` links one student to one attendance session after both required identity checks succeed.

Academic records are deactivated rather than deleted where historical relationships must be preserved. Foreign-key relationships use protected deletion where removing a referenced record would compromise academic or attendance history.

## Technology stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12 and Django 5.2 |
| Frontend | Django Templates, HTML, CSS and JavaScript |
| Database | PostgreSQL; production database hosted on Neon |
| Database URL handling | `dj-database-url` and Psycopg 3 |
| Application server | Gunicorn |
| Static assets | WhiteNoise |
| Hosting | Render |
| Version control | Git and GitHub |

## Project structure

```text
rollnexa/
    accounts/          Authentication, profiles, roles and user management
    academics/         Institutional structure, courses, offerings and registration
    attendance/        Attendance sessions, records and verification service boundary
    config/            Django settings and URL configuration
    core/              Home page and shared health/error views
    static/            CSS, JavaScript, images and downloadable CSV data
    templates/         Django HTML templates
    manage.py          Django management entry point
    requirements.txt   Python dependencies
    build.sh           Render build, static collection and migration commands
    render.yaml        Render service configuration
    README.md          Project description and local development guide
```

## Local development setup

### Requirements

- Python 3.12.10 (the version configured for the hosted service).
- PostgreSQL.
- Git.
- A terminal or IDE capable of setting environment variables.

### 1. Obtain the source code

```bash
git clone https://github.com/Davidnna/RollNexa.git
cd RollNexa
```

If the repository is already cloned, change into the repository directory and pull the latest approved update before continuing.

### 2. Create and activate a virtual environment

On macOS or Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Create a development PostgreSQL database

Create a separate database for local development. Do not point local experiments at the production database.

For example, connect to PostgreSQL as a database administrator and run:

```sql
CREATE ROLE rollnexa_dev WITH LOGIN PASSWORD 'replace-this-password';
CREATE DATABASE rollnexa_dev OWNER rollnexa_dev;
```

The local connection URL will have this form:

```text
postgresql://rollnexa_dev:replace-this-password@127.0.0.1:5432/rollnexa_dev
```

The project requires `DATABASE_URL`. In debug mode, local PostgreSQL connections do not require TLS. Non-debug deployments require a TLS-enabled PostgreSQL connection.

### 5. Configure environment variables

The `.env.example` file documents the available settings, but the application does not automatically load `.env` files. Set the variables in your terminal or IDE run configuration.

On macOS or Linux:

```bash
export DEBUG=True
export SECRET_KEY='replace-with-a-long-random-local-secret'
export ALLOWED_HOSTS='localhost,127.0.0.1'
export CSRF_TRUSTED_ORIGINS='http://localhost:8000'
export DATABASE_URL='postgresql://rollnexa_dev:replace-this-password@127.0.0.1:5432/rollnexa_dev'
export BOOTSTRAP_ADMIN_TOKEN='replace-with-a-one-time-local-token'
```

On Windows PowerShell:

```powershell
$env:DEBUG = 'True'
$env:SECRET_KEY = 'replace-with-a-long-random-local-secret'
$env:ALLOWED_HOSTS = 'localhost,127.0.0.1'
$env:CSRF_TRUSTED_ORIGINS = 'http://localhost:8000'
$env:DATABASE_URL = 'postgresql://rollnexa_dev:replace-this-password@127.0.0.1:5432/rollnexa_dev'
$env:BOOTSTRAP_ADMIN_TOKEN = 'replace-with-a-one-time-local-token'
```

These environment variables apply to the current terminal session. Configure them again when opening a new terminal, or store them in your IDE's local run configuration. Never commit secrets or a populated `.env` file.

`DIRECT_DATABASE_URL` is used by the hosted build for direct, non-pooled database migrations when configured. It is not required for a normal local run.

### 6. Run database migrations and checks

```bash
python manage.py check
python manage.py migrate
```

To verify that model definitions and migrations are aligned:

```bash
python manage.py makemigrations --check --dry-run
```

### 7. Create the first system administrator

Start the development server:

```bash
python manage.py runserver
```

Open the one-time setup page:

```text
http://127.0.0.1:8000/setup/initial-admin/
```

Enter the `BOOTSTRAP_ADMIN_TOKEN` configured in step 5 and complete the administrator form. The route is available only when a bootstrap token is configured and no superuser exists. After creating the administrator, remove `BOOTSTRAP_ADMIN_TOKEN` from the environment and restart the application.

### 8. Sign in and use the application

Open:

```text
http://127.0.0.1:8000/accounts/login/
```

Sign in with the administrator account. Create or import the institutional structure, configure the academic session and semesters, add courses and offerings, create lecturer accounts, assign lecturers to offerings, and configure student accounts and registrations before testing lecturer attendance-session management.

### 9. Run the automated test suite

```bash
python manage.py test
```

Run the Django system check and migration check before submitting changes or deploying an update:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Main application routes

| Purpose | Route |
| --- | --- |
| Home | `/` |
| Sign in | `/accounts/login/` |
| Initial administrator setup | `/setup/initial-admin/` |
| Administrator dashboard | `/dashboard/admin/` |
| Lecturer dashboard | `/dashboard/lecturer/` |
| Student dashboard | `/dashboard/student/` |
| Academic management | `/management/academic/` |
| Academic structure CSV import | `/management/academic/import/` |
| Academic sessions and semesters CSV import | `/management/academic/sessions/import/` |
| Course management | `/management/courses/` |
| Course CSV import | `/management/courses/import/` |
| Student course registration | `/student/courses/` |
| Lecturer teaching and rosters | `/lecturer/courses/` |
| Lecturer attendance sessions | `/lecturer/attendance/` |

Attendance-session actions are available from the lecturer session detail page. Activation, closure and cancellation are POST-only actions protected by authentication, role checks and active teaching-assignment checks.

## Attendance session rules in version 0.6.0

- Only an active lecturer with an active teaching assignment can schedule a session for that course offering.
- The course offering and its academic parent records must be active.
- The session end time must be later than its start time.
- Overlapping non-cancelled sessions for the same offering are rejected.
- A scheduled session can be activated only within its configured time window.
- A scheduled session can be cancelled; an active session can be closed.
- A session is not open for attendance recording outside its configured time window, even if its status has not yet been changed from active to closed.
- Only currently registered, active students whose programme and level match the offering are eligible for attendance recording.
- The database permits at most one attendance record for a student in a session.
- Both QR and facial verification must succeed, with QR verification occurring first. Failure or absence of either check must prevent a present record.

## Academic CSV imports and included EBSU starter data

System administrators can use the import pages to validate and preview CSV files before explicitly confirming an atomic import:

- Academic structure import: `/management/academic/import/`.
- Academic session and semester import: `/management/academic/sessions/import/`.
- Course catalogue and course offering import: `/management/courses/import/`.

The importers do not delete or deactivate records. Internal codes in the starter files are RollNexa identifiers and are not necessarily official institutional codes. Keep identifiers stable between imports.

The `static/downloads/` directory includes EBSU-oriented starter datasets and templates, including:

- `ebsu_academic_structure.csv`: a starter faculty, department and programme structure. Some groupings and programme details require confirmation by the institution.
- `ebsu_computer_science_courses.csv`: 69 Computer Science course rows based on the published EBSU Computer Science department curriculum page. The page does not identify the academic session to which the curriculum applies.
- `ebsu_science_curriculum_expanded.csv`: 785 programme-specific course offerings across 11 Science programmes, based on published departmental curriculum pages.
- `ebsu_course_curriculum_coverage.csv`: a coverage register for 81 programmes in the imported academic structure.
- Blank RollNexa CSV templates for academic sessions and course catalogue data.

These datasets are development and testing baselines, not Registrar-certified course registration handbooks. Some department mappings, course ownership, elective rules and curriculum details remain unresolved or require departmental confirmation. Verify all academic data against current approved institutional records before opening real student registration. Academic sessions and semesters must be verified against the current approved academic calendar; the application does not infer which period is current.

## Production deployment

The hosted application uses the existing Render web service and Neon PostgreSQL database:

- Application: `https://rollnexa.onrender.com/`
- GitHub repository: `https://github.com/Davidnna/RollNexa`
- Hosting: Render.
- Production database: Neon PostgreSQL.

The Render build command in `build.sh` installs the Python requirements, runs `python manage.py check`, collects static files and applies migrations. When `DIRECT_DATABASE_URL` is configured, migrations use that direct database connection; the running application uses `DATABASE_URL`, which should be the Neon pooled connection URL.

For an update, use the existing GitHub repository, branch and Render service. Do not create a replacement production database, reset migrations or manually delete production records. Review the deployment logs and confirm that migrations complete before testing the updated application.

## Security and data protection

- Never commit `.env` files, database URLs, passwords, API keys, bootstrap tokens or private student data.
- Use a separate development database and test accounts for local development.
- Enforce authorization on the server; client-side visibility is not security.
- Remove the one-time `BOOTSTRAP_ADMIN_TOKEN` after the first administrator has been created.
- Do not collect or use real student biometric data until institutional approval and appropriate privacy, lawful-basis, security, access-control, retention, deletion and backup arrangements have been established.
- Store biometric templates only when a later release implements an approved design. Avoid unnecessary retention of raw facial images.
- Do not claim that QR Code or facial recognition is infallible. The two checks provide separate controls and must be tested against spoofing, false acceptance and false rejection risks.
- RollNexa is a software prototype. Do not imply institutional endorsement, regulatory certification or production-grade biometric assurance without independent evidence.

## Brand reference

- Brand name: **RollNexa**.
- Tagline: **Attendance, connected.**
- Primary colours: Midnight Navy `#111B35`, Electric Teal `#19C8B6`, Deep Teal `#0D968B`, Soft Aqua `#7CE6DC`, Cloud Mist `#F3F7FB` and Slate `#52637C`.
- Display typography: Manrope. Interface and body typography: Inter, with system sans-serif fallbacks.

## Release history

- **0.4.0:** Course catalogue, programme-specific course offerings, lecturer assignments, student registration and lecturer class rosters.
- **0.4.1:** Course catalogue and offering CSV import with validation and preview.
- **0.4.2:** Academic session and semester CSV import.
- **0.4.3:** Programme-specific offering credit units and curriculum classifications, source provenance and expanded EBSU Science starter data.
- **0.5.0:** Lecturer directory, profile management, teaching-assignment register, cross-department assignment support and assignment revocation history.
- **0.6.0:** Attendance-session management and the database/service foundation for dual QR Code and Facial Recognition verification.
