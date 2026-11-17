# RollNexa 0.9.1

**Attendance, connected.**

RollNexa is an academic administration and smart attendance platform. It connects institutional structure, user accounts, academic sessions, course catalogues, course offerings, lecturer assignments, student registrations and attendance-session management. Its attendance policy requires both QR Code verification and facial identity verification to succeed, in that order, before a present record can be created.

Version 0.9.1 improves the academic workflows in the React-based role workspaces. Administrators can open or close registration across all active course offerings, assign one lecturer to multiple programme offerings of the same course delivery group, review field-specific validation errors and receive a prominent one-time temporary-password dialog after account creation. The public website, authenticated React application and Django REST API are served from the same origin. Django remains the source of truth for authentication, authorisation, business rules, validation and database operations.

This release adds API operations and React interface changes without introducing a database schema migration. Global registration actions update the existing `CourseOffering.registration_open` flags for all currently active and academically eligible offerings. Individual offerings can still be closed separately after a global opening action.

## 1. Version 0.9.1 scope

### Platform capabilities

- Public website for Home, About, Features, How It Works, Contact, Privacy and Terms.
- React 19 and TypeScript authenticated application.
- Role-specific workspaces for system administrators, lecturers and students.
- Session-based authentication using existing Django user accounts and CSRF protection.
- Administrator account management, including account creation, profile updates and account activation or deactivation.
- Temporary passwords for administrator-created accounts, with mandatory password change at first sign-in.
- Academic structure management for faculties, departments, programmes, academic sessions and semesters.
- Current academic session and current semester selection.
- Course catalogue management and course offering management.
- Lecturer teaching assignments, bulk assignment across programme offerings of the same course, semester and level, revocation and retained assignment history.
- Global opening and closing of registration for all active course offerings, with individual offering controls retained.
- Student course discovery, registration and withdrawal where registration is open.
- Lecturer course workspace and registered-student class rosters.
- Lecturer attendance-session scheduling, activation, closure and cancellation.
- Rotating session QR Code display for authorised lecturers.
- Student QR Code scanning using the device camera or a direct RollNexa check-in link.
- Short-lived, cryptographically signed QR tokens with server-side session, lecturer-assignment, account and course-registration validation.
- Pending QR verification records with expiry, duplicate-attempt protection and status visibility.
- Administrator attendance-session monitoring.
- Student verified attendance history.
- Role-scoped academic and attendance summary reports.
- Profile updates and password management.
- Search, status filters, pagination, form validation feedback and responsive workspace layouts.
- Field-level validation messages with visible error highlighting in React forms.
- Prominent one-time temporary-password dialog with copy action after successful administrator account creation.
- Docker multi-stage build for the React frontend and Django application.
- Existing Django management views retained during migration as a fallback for workflows not yet represented in React.

### Attendance implementation status

The attendance session foundation and lifecycle management are implemented. Version 0.9.0 generates rotating, short-lived signed QR Codes for active sessions and allows eligible students to scan them. The server validates the signed token, active session window, issuing lecturer assignment, student account, programme, level and course registration. The browser camera decodes the QR locally; only the signed token is sent to Django. A successful scan creates a pending QR verification record, not an attendance record.

QR tokens are signed using Django's signing framework and are not stored in plaintext. The lecturer display requests a new token every 30 seconds; each token is valid for up to 60 seconds. A pending QR verification expires after five minutes or at the end of the attendance session, whichever occurs first. Repeated scans reuse an unexpired pending verification for the same student and session.

Version 0.9.0 does **not** enrol student faces, capture facial images, perform liveness detection or run a facial-recognition model. Student attendance is therefore not yet fully operational. An `AttendanceRecord` is still created only after both QR Code and facial verification succeed in the required order and all session, registration and integrity checks pass. QR verification alone never marks a student present. The attendance-recording service requires a persisted verification attempt in the server-side `face_verified` state; it does not accept browser-supplied success booleans. No manual attendance-entry interface is provided.

A rotating QR Code limits the useful lifetime of a copied image but does not independently prove physical proximity. A valid code can still be forwarded to another eligible student during its short validity window. The required facial identity check remains the second control; additional proximity safeguards may be evaluated separately.

The QR API surface is:

- `GET /api/v1/attendance/sessions/{session_id}/qr/` — lecturer-only issuance of a short-lived signed token for an active assigned session.
- `POST /api/v1/attendance/verify-qr/` — student-only QR token verification and creation or reuse of a pending verification attempt.
- `GET /api/v1/attendance/verifications/{verification_id}/` — student-only status lookup for the student's own verification attempt.

The face-completion service is an internal server-side boundary and is not exposed as an API accepting a client-supplied success flag.

## 2. Attendance verification policy

RollNexa uses **QR Code AND Facial Recognition**, not either method independently.

1. An authorised lecturer schedules and activates an attendance session for an assigned course offering.
2. A student must be eligible for the course offering and access the active session.
3. The student scans the rotating QR Code. The server validates its signature and expiry, then checks the active session, issuing lecturer assignment and student course registration.
4. A successful QR scan creates a pending verification attempt. It does not create an attendance record.
5. Facial Recognition must then successfully verify the student's identity against an enrolled reference.
6. Both verification timestamps must fall within the active session window and the pending verification must remain valid.
7. The server records attendance only when both checks succeed and all eligibility and integrity checks pass.

If either verification fails or is missing, no present record is created. QR generation and scanning are operational in this release; face enrolment, liveness detection and facial recognition will be introduced in a later release. The frontend must distinguish the operational QR stage from the planned facial stage.

## 3. User roles and permissions

| Role | React workspace capabilities |
| --- | --- |
| System administrator | Manage user accounts, faculties, departments, programmes, academic sessions, semesters, course catalogue, course offerings, lecturer assignments; monitor attendance sessions; review platform reports. |
| Lecturer | View assigned course offerings, review registered student rosters, schedule attendance sessions, activate or close sessions, display rotating session QR Codes, review QR verification counts and role-scoped reports. |
| Student | View eligible course offerings, register or withdraw where registration is open, scan an active session QR Code, review verified attendance history and update personal contact details. |

The administrator role is represented by Django superuser accounts. Lecturer and student roles are stored on `UserProfile`. Permissions are enforced by Django API views and services. Hiding a link or action in React is not treated as an access-control mechanism.

## 4. Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite |
| UI styling | Tailwind CSS and project CSS |
| Frontend routing | React Router |
| API state | TanStack React Query |
| QR rendering | qrcode.react |
| Camera QR scanning | html5-qrcode |
| Backend | Python 3.12 and Django 5.2 |
| API | Django REST Framework |
| Authentication | Django session authentication and CSRF protection |
| Database | PostgreSQL; production database hosted on Neon |
| Database URL handling | `dj-database-url` and Psycopg 3 |
| Application server | Gunicorn |
| Static assets | WhiteNoise |
| Container build | Docker multi-stage build with Node.js 22 and Python 3.12 |
| Hosting | Render |
| Version control | Git and GitHub |

## 5. Application architecture

The React application and Django API are served from the same origin. Django remains responsible for authentication, authorisation, validation, academic rules, attendance rules and database operations.

```text
rollnexa/
    accounts/              Authentication, profiles, roles and user management
    academics/             Institutional structure, courses and registration
    api/                   Versioned REST API, workspace endpoints and API tests
    attendance/            Attendance sessions, records and verification service
    config/                Django settings and URL configuration
    core/                  Health and shared application views
    frontend/              React, TypeScript, Vite and frontend styles
        src/
            context/       Authentication context
            layouts/       Public and authenticated layouts
            lib/           API client and shared utilities
            pages/         Public pages, dashboards and workspace modules
    static/                Existing static assets and downloadable datasets
    templates/             Existing Django templates retained during migration
    Dockerfile             Multi-stage frontend and backend image build
    docker-entrypoint.sh   Production migration and Gunicorn startup
    manage.py              Django management entry point
    requirements.txt       Python dependencies
    render.yaml            Render service configuration
    build.sh               Local build helper
    VERSION                Current release version
    README.md              Project description and local development guide
```

### Public website routes

- `/` — Home
- `/about/` — About RollNexa
- `/features/` — Platform capabilities and implementation status
- `/how-it-works/` — Attendance verification workflow
- `/contact/` — Institutional access and contact guidance
- `/privacy/` — Privacy information and biometric safeguards
- `/terms/` — Preliminary terms of use
- `/login/` — Sign-in page

The Privacy and Terms pages are product-level drafts. The institution deploying RollNexa must review and approve its controller details, lawful basis, retention rules, contact route and binding terms before operational use, particularly before enabling biometric processing.

### Authenticated application routes

- `/app/` — Role-aware dashboard overview
- `/app/users/` — Administrator user management
- `/app/academic/` — Faculties, departments, programmes, academic sessions and semesters
- `/app/courses/` — Course catalogue, course offerings, teaching assignments, lecturer courses or student course registration according to role
- `/app/rosters/` — Lecturer class rosters
- `/app/attendance/` — Lecturer attendance sessions, administrator monitoring or student attendance feature status according to role
- `/app/history/` — Student verified attendance history
- `/app/reports/` — Role-scoped academic and attendance summaries
- `/app/profile/` — Personal profile management
- `/app/settings/` — Account settings and profile access
- `/app/password-change/` — Authenticated password change

The navigation and accessible API resources are scoped to the signed-in role. A student cannot access administrative management endpoints; lecturers cannot access administrator management endpoints or another lecturer's class roster or attendance sessions.

### API routes

All API endpoints are under `/api/v1/`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/v1/csrf/` | Initialise a CSRF cookie and return the CSRF token. |
| GET | `/api/v1/auth/session/` | Return the current authentication state and user profile. |
| POST | `/api/v1/auth/login/` | Authenticate with username and password and establish a Django session. |
| POST | `/api/v1/auth/logout/` | End the current Django session. |
| POST | `/api/v1/auth/password-change/` | Validate and update the authenticated user's password. |
| GET | `/api/v1/dashboard/summary/` | Return dashboard summary data scoped to the authenticated user's role. |
| GET, PATCH | `/api/v1/workspace/profile/` | Read or update the authenticated user's permitted profile fields. |
| GET | `/api/v1/workspace/reports/` | Return administrator or lecturer scoped report summaries. |
| GET, POST | `/api/v1/workspace/users/` | List users or create a lecturer/student account; administrator only. |
| GET, PATCH | `/api/v1/workspace/users/{id}/` | Read or update an account; administrator only. |
| POST | `/api/v1/workspace/users/{id}/toggle/` | Activate or deactivate an account; administrator only. |
| GET, POST | `/api/v1/workspace/{academic-resource}/` | List or create faculties, departments, programmes, sessions or semesters; administrator only. |
| GET, PATCH | `/api/v1/workspace/{academic-resource}/{id}/` | Read or update an academic record; administrator only. |
| POST | `/api/v1/workspace/{academic-resource}/{id}/toggle/` | Activate or deactivate an academic record; administrator only. |
| POST | `/api/v1/workspace/{sessions-or-semesters}/{id}/set-current/` | Select the current academic session or semester; administrator only. |
| GET, POST | `/api/v1/workspace/courses/` | List or create course catalogue entries; administrator only. |
| GET, PATCH | `/api/v1/workspace/courses/{id}/` | Read or update a course; administrator only. |
| POST | `/api/v1/workspace/courses/{id}/toggle/` | Activate or deactivate a course; administrator only. |
| GET, POST | `/api/v1/workspace/offerings/` | List or create course offerings; administrator only. |
| GET, PATCH | `/api/v1/workspace/offerings/{id}/` | Read or update an offering; administrator only. |
| POST | `/api/v1/workspace/offerings/{id}/toggle/` | Activate or deactivate an offering; administrator only. |
| POST | `/api/v1/workspace/offerings/{id}/assign/` | Assign a lecturer to an offering; administrator only. |
| GET, POST | `/api/v1/workspace/assignments/` | List teaching assignments or create an assignment; administrator only. |
| GET | `/api/v1/workspace/assignment-options/` | Return lecturers, courses, semesters, levels and matching programme offerings for bulk assignment; administrator only. |
| POST | `/api/v1/workspace/assignments/bulk/` | Assign one lecturer to multiple programme offerings for the same course, semester and level; administrator only. |
| POST | `/api/v1/workspace/assignments/{id}/revoke/` | Revoke an active assignment and retain its history; administrator only. |
| POST | `/api/v1/workspace/registration-control/` | Open or close registration for all active course offerings; administrator only. |
| GET | `/api/v1/workspace/lecturer-courses/` | List active course offerings assigned to the lecturer. |
| GET | `/api/v1/workspace/rosters/?offering={id}` | List registered students for an offering assigned to the lecturer. |
| GET | `/api/v1/workspace/student-courses/` | List offerings matching the student's programme and level. |
| POST | `/api/v1/workspace/student-courses/{offering-id}/register/` | Register the authenticated student where registration is open. |
| POST | `/api/v1/workspace/student-courses/{offering-id}/withdraw/` | Withdraw the authenticated student where withdrawal is open. |
| GET, POST | `/api/v1/workspace/attendance-sessions/` | List or schedule attendance sessions; lecturers can manage only assigned offerings. |
| POST | `/api/v1/workspace/attendance-sessions/{id}/activate/` | Activate a scheduled attendance session. |
| POST | `/api/v1/workspace/attendance-sessions/{id}/close/` | Close an active attendance session. |
| POST | `/api/v1/workspace/attendance-sessions/{id}/cancel/` | Cancel a scheduled attendance session. |
| GET | `/api/v1/workspace/attendance-monitor/` | Administrator read-only view of institution-wide attendance sessions. |
| GET | `/api/v1/workspace/attendance-history/` | Return verified attendance records belonging to the authenticated student. |

Workspace list endpoints support pagination using `page` and `page_size`. Applicable list endpoints support text search using `q` and status filtering using `status`. The API returns JSON validation errors for invalid forms and rejects requests from roles outside the resource's permitted scope.

The API uses Django session authentication. Mutating requests must include the CSRF token in the `X-CSRFToken` header. Session cookies are HTTP-only and use `SameSite=Lax`; secure-cookie flags are enabled when `DEBUG` is false. No JWT is stored in browser local storage.

## 6. Academic and attendance data model

- A `Faculty` contains departments.
- A `Department` belongs to one faculty and contains programmes.
- A `Programme` belongs to one department. Award and duration are optional when an official source does not confirm them.
- An `AcademicSession` contains semesters. At most one academic session and one semester can be current at a time; a current semester must belong to the current session.
- A student profile can reference a programme and current level. The student's department is derived from the programme's department.
- A lecturer profile can reference a department.
- A master `Course` is owned by a department and stores the shared course identity.
- A `CourseOffering` delivers a course to a specific programme, semester and level. The same master course can be offered to multiple programmes, with programme-specific credit units and curriculum classifications.
- A `CourseLecturerAssignment` links a lecturer to a course offering and retains assignment revocation history.
- A `CourseRegistration` links a student to a course offering and records registered or withdrawn status. Re-registration updates the existing registration row.
- An `AttendanceSession` belongs to one course offering and records its scheduled time window and lifecycle.
- An `AttendanceRecord` links one student to one attendance session after both required identity checks succeed.

Academic records are deactivated rather than deleted where historical relationships must be preserved. Foreign-key relationships use protected deletion where removing a referenced record would compromise academic or attendance history.

## 7. Local development setup

### Requirements

- Python 3.12.x.
- Node.js 22.x and npm.
- PostgreSQL.
- Git.
- Docker Desktop or Docker Engine for local container testing (optional).

### 1. Obtain the source code

```bash
git clone https://github.com/Davidnna/RollNexa.git
cd RollNexa
```

If the repository is already cloned, change into the repository directory and pull the latest approved update before continuing.

### 2. Create and activate a Python virtual environment

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

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Create a local PostgreSQL database

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

### 5. Configure backend environment variables

The `.env.example` file documents the available settings, but Django does not automatically load `.env` files. Set the variables in your terminal or IDE run configuration.

On macOS or Linux:

```bash
export DEBUG=True
export SECRET_KEY='replace-with-a-long-random-local-secret'
export ALLOWED_HOSTS='localhost,127.0.0.1'
export CSRF_TRUSTED_ORIGINS='http://localhost:5173,http://127.0.0.1:5173'
export DATABASE_URL='postgresql://rollnexa_dev:replace-this-password@127.0.0.1:5432/rollnexa_dev'
export BOOTSTRAP_ADMIN_TOKEN='replace-with-a-one-time-local-token'
```

On Windows PowerShell:

```powershell
$env:DEBUG = 'True'
$env:SECRET_KEY = 'replace-with-a-long-random-local-secret'
$env:ALLOWED_HOSTS = 'localhost,127.0.0.1'
$env:CSRF_TRUSTED_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173'
$env:DATABASE_URL = 'postgresql://rollnexa_dev:replace-this-password@127.0.0.1:5432/rollnexa_dev'
$env:BOOTSTRAP_ADMIN_TOKEN = 'replace-with-a-one-time-local-token'
```

These variables apply only to the current terminal session. Configure them again when opening a new terminal, or store them in your IDE's local run configuration. Never commit secrets or a populated `.env` file.

### 6. Apply migrations and create the first administrator

```bash
python manage.py check
python manage.py migrate
python manage.py runserver 8000
```

Open the one-time setup route in a browser:

```text
http://127.0.0.1:8000/setup/initial-admin/
```

Enter the `BOOTSTRAP_ADMIN_TOKEN` configured in step 5 and complete the administrator form. The route is available only when a bootstrap token is configured and no superuser exists. After creating the administrator, remove `BOOTSTRAP_ADMIN_TOKEN` from the environment.

### 7. Install frontend dependencies

Open a second terminal in the repository root:

```bash
cd frontend
npm install
```

The first installation generates `frontend/package-lock.json`. Keep that lockfile in Git so subsequent installs and Docker builds can use the exact resolved dependency tree. The QR workflow uses `qrcode.react` to render lecturer codes and `html5-qrcode` to scan them with a device camera.

### 8. Start the React development server

From the `frontend/` directory:

```bash
npm run dev
```

Open:

```text
http://localhost:5173/
```

Vite serves the React application and proxies `/api/`, `/static/`, legacy Django paths and `/healthz` to the Django development server on port 8000. The development CSRF trusted origins are configured in Django when `DEBUG=True`.

### 9. Build the frontend and serve it through Django

From the repository root:

```bash
npm --prefix frontend install
npm --prefix frontend run build
python manage.py collectstatic --noinput
python manage.py runserver 8000
```

Open `http://127.0.0.1:8000/`. Django serves the built React application and WhiteNoise serves the compiled frontend assets. The built output is generated under `static/frontend/` and is excluded from Git; Docker builds it from the source in `frontend/`.

### 10. Run checks and tests

Backend:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

Run these checks before committing a release. Also test account creation and deactivation, temporary-password dialog and copy action, field-level validation highlighting, academic record management, global registration open/close actions, individual offering registration settings, bulk lecturer assignment across programme offerings, assignment history and revocation, student registration and withdrawal, class rosters, attendance session lifecycle actions, QR display and 30-second rotation, student camera scanning, token expiry, unregistered-student rejection, duplicate-scan handling, closed-session rejection, report scope, profile updates, login, logout and forced password change in a browser.

## 8. Docker development and deployment

### Build the image locally

From the repository root:

```bash
docker build -t rollnexa:0.9.1 .
```

Run the container with the required environment variables configured. Use a local or development PostgreSQL database, not the production database, for local container tests.

```bash
docker run --rm -p 8000:8000 --env-file .env rollnexa:0.9.1
```

The container entrypoint applies Django migrations and then starts Gunicorn. If `DIRECT_DATABASE_URL` is configured, migrations use that connection; the running application continues to use `DATABASE_URL`.

### Render deployment

The `render.yaml` Blueprint configures the RollNexa web service to use the Docker runtime. The Dockerfile:

1. Installs frontend dependencies in a Node.js 22 build stage.
2. Builds the React application into `static/frontend/`.
3. Installs Python dependencies in a Python 3.12 runtime stage.
4. Copies the Django application and compiled frontend assets into the runtime image.
5. Runs `collectstatic` during image construction.
6. Applies database migrations at container startup and launches Gunicorn.

Retain the existing Render service name, repository, branch, region, environment variables and Neon database connection values when synchronising the Blueprint. Review the Blueprint preview before applying deployment changes. Do not create a replacement database, reset migrations or delete production records.

Required production environment variables:

- `DATABASE_URL` — the Neon pooled PostgreSQL connection used by the running application.
- `DIRECT_DATABASE_URL` — the Neon direct connection used for migrations, if available.
- `SECRET_KEY` — a strong secret generated or configured in Render.
- `DEBUG=false`.
- `WEB_CONCURRENCY=1` for the current service configuration.

Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` if a custom domain is used. Render's service hostname is added to the trusted host and CSRF origin settings automatically.

After deployment, verify `/healthz`, the public website, sign-in and sign-out, each role's dashboard, user and academic management, course registration, lecturer rosters, attendance session lifecycle actions, reports, profile updates, the Django administration site and the retained legacy management routes. Review deployment logs and confirm migrations completed successfully.

## 9. Security and privacy requirements

- Enforce role permissions on the Django backend and API.
- Use Django session authentication; do not store authentication tokens in browser local storage.
- Require CSRF tokens for state-changing API requests.
- Keep session cookies HTTP-only and secure in production.
- Apply rate limiting to API login attempts.
- Keep secrets in environment variables and out of Git.
- Temporary passwords for new accounts must be delivered only to the authorised administrator at account creation and must be changed at first sign-in.
- Do not expose raw biometric data in URLs, logs or client-side storage.
- Do not collect or store facial images or biometric templates until institutional privacy, retention, encryption, access-control and deletion requirements are approved and implemented.
- Preserve academic and attendance history through protected relationships and controlled deactivation.
- Do not manually create or alter verified attendance records through a dashboard action.

## 10. Release conventions

Every RollNexa update must follow these project rules:

1. Every release must include a clear GitHub commit message.
2. All code must use four spaces per indentation level. Do not mix tabs and spaces.
3. `README.md` is the only Markdown file permitted in the repository unless the project owner explicitly approves another Markdown file.
4. `README.md` contains the software description and the guide for running the software locally.
5. Extend the existing application. Do not replace working functionality or reset production data without explicit approval.
6. Each release must include source validation and the relevant backend and frontend test results. Do not describe checks as passed if they were not executed.

### Version 0.9.1 GitHub commit message

```text
Improve global course registration, bulk lecturer assignments and account creation UX in RollNexa 0.9.1
```

## 11. Development roadmap

| Release | Objective |
| --- | --- |
| 0.7.0 | React foundation, public website, session-authenticated API and dashboard shell. |
| 0.8.0 | Complete administrator, lecturer and student dashboards and migrate core management workflows to React. |
| 0.9.0 | Secure dynamic QR Code generation, scanning, short-lived signed tokens, pending verification records and server-side validation. |
| 0.9.1 | Global registration controls, bulk lecturer assignment across programme offerings, field-level validation feedback and prominent temporary-password dialog. |
| 1.0.0 | Facial enrolment, facial recognition, liveness safeguards, integrated dual verification and comprehensive testing. |

The roadmap is a development plan. A feature becomes operational only after implementation, testing and deployment in the corresponding release.
