# RollNexa 0.7.0

**Attendance, connected.**

RollNexa is an academic administration and smart attendance platform. It connects institutional structure, user accounts, academic sessions, course catalogues, course offerings, lecturer assignments, student registrations and attendance-session management. Its attendance policy requires both QR Code verification and facial identity verification to succeed, in that order, before a present record can be created.

Version 0.7.0 introduces a React and TypeScript frontend, a Django REST API, session-based API authentication, a public website, role-aware dashboard workspaces and a Docker-based deployment build. Existing Django business logic, database records and legacy management screens are retained while the user interface is migrated in stages.

## 1. Version 0.7.0 scope

### Implemented in the backend

- User authentication and account profiles.
- System administrator, lecturer and student roles.
- Faculty, department and programme management.
- Academic session and semester management.
- Course catalogue and programme-specific course offerings.
- Lecturer-course assignments and assignment history.
- Student course registration and withdrawal.
- Lecturer class rosters.
- Attendance-session scheduling, activation, closure and cancellation.
- Lecturer authorisation for attendance-session management.
- Student course-registration eligibility checks.
- An attendance-record model with one record per student per session.
- A server-side attendance service that requires successful QR and facial verification outcomes, both verification timestamps, and QR verification before facial verification.

### Introduced in version 0.7.0

- React 19 and TypeScript frontend, built with Vite.
- Public pages for Home, About, Features, How It Works, Contact, Privacy and Terms.
- React sign-in page and role-aware authenticated application shell.
- Administrator, lecturer and student dashboard navigation.
- Authenticated dashboard summary endpoint using existing database records.
- Session status, login, logout and password-change API endpoints.
- CSRF-protected session authentication using Django's existing user accounts.
- React Query for API state and React Router for navigation.
- Docker multi-stage build for the React assets and Django application.
- Render Blueprint configuration for the Docker runtime.

### Migration status

Version 0.7.0 establishes the React application and dashboard foundation. Existing Django management screens remain available while their workflows are migrated. Some React workspace sections intentionally direct authorised users to the existing Django screens until the corresponding React modules are completed.

The current release does not generate or scan QR Codes, enrol student faces, capture facial images, perform liveness detection or run a facial-recognition model. Attendance analytics, absence calculation, report exports and student attendance check-in are also not yet operational.

## 2. Attendance verification policy

RollNexa uses **QR Code AND Facial Recognition**, not either method independently.

1. An authorised lecturer schedules and activates an attendance session for an assigned course offering.
2. A student must be eligible for the course offering and access the active session.
3. QR Code verification must succeed first.
4. Facial Recognition must then successfully verify the student's identity against an enrolled reference.
5. Both verification timestamps must fall within the active session window.
6. The server records attendance only when both checks succeed and all eligibility and integrity checks pass.

If either verification fails or is missing, no present record is created. QR Code generation, face enrolment, liveness detection and recognition will be introduced in later releases. The 0.7.0 frontend must not imply that these planned verification capabilities are already operational.

## 3. User roles

| Role | Responsibilities |
| --- | --- |
| System administrator | Manage user accounts, institutional structure, academic sessions, semesters, course catalogue, course offerings and lecturer assignments; review administrative records. |
| Lecturer | View assigned course offerings and registered student rosters; schedule, activate, close and cancel attendance sessions for assigned offerings. |
| Student | View eligible course offerings and manage course registration or withdrawal where registration rules permit. Student attendance check-in is planned for a later release. |

Permissions are enforced by Django views, API permissions and services. Hiding a link in React is not treated as an access-control mechanism.

## 4. Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite |
| UI styling | Tailwind CSS and project CSS |
| Frontend routing | React Router |
| API state | TanStack React Query |
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

The React application and Django API are served from the same origin. Django remains the source of truth for authentication, authorisation, validation, academic rules and database operations.

```text
rollnexa/
    accounts/              Authentication, profiles, roles and user management
    academics/             Institutional structure, courses and registration
    api/                   Versioned REST API and API tests
    attendance/            Attendance sessions, records and verification service
    config/                Django settings and URL configuration
    core/                  Health and shared application views
    frontend/              React, TypeScript, Vite and frontend styles
        src/
            context/       Authentication context
            layouts/       Public and authenticated layouts
            lib/           API client and shared utilities
            pages/         Public pages and dashboard pages
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
- `/app/users/` — Administrator user workspace
- `/app/academic/` — Administrator academic structure workspace
- `/app/courses/` — Course workspace
- `/app/rosters/` — Lecturer roster workspace
- `/app/attendance/` — Attendance workspace
- `/app/history/` — Student attendance history workspace
- `/app/reports/` — Reporting workspace
- `/app/profile/` — Profile workspace
- `/app/settings/` — Settings workspace
- `/app/password-change/` — Authenticated password change

The dashboard navigation is role-aware. A workspace that has not yet been migrated to React provides a link to its existing Django management screen where one exists.

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

The first installation generates `frontend/package-lock.json`. Keep that lockfile in Git so subsequent installs and Docker builds can use the exact resolved dependency tree.

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

Run these checks before committing a release. Also test login, logout, forced password change, role-based dashboard access and the legacy management routes in a browser.

## 8. Docker development and deployment

### Build the image locally

From the repository root:

```bash
docker build -t rollnexa:0.7.0 .
```

Run the container with the required environment variables configured. Use a local or development PostgreSQL database, not the production database, for local container tests.

```bash
docker run --rm -p 8000:8000 --env-file .env rollnexa:0.7.0
```

The container entrypoint applies Django migrations and then starts Gunicorn. If `DIRECT_DATABASE_URL` is configured, migrations use that connection; the running application continues to use `DATABASE_URL`.

### Render deployment

The `render.yaml` Blueprint changes the existing RollNexa web service configuration to the Docker runtime. The Dockerfile:

1. Installs frontend dependencies in a Node.js 22 build stage.
2. Builds the React application into `static/frontend/`.
3. Installs Python dependencies in a Python 3.12 runtime stage.
4. Copies the Django application and compiled frontend assets into the runtime image.
5. Runs `collectstatic` during image construction.
6. Applies database migrations at container startup and launches Gunicorn.

Retain the existing Render service name, repository, branch, region, environment variables and Neon database connection values when synchronising the Blueprint. Confirm the Docker runtime and deployment settings in the Render Blueprint preview before applying the change. Do not create a replacement database, reset migrations or delete production records.

Required production environment variables:

- `DATABASE_URL` — the Neon pooled PostgreSQL connection used by the running application.
- `DIRECT_DATABASE_URL` — the Neon direct connection used for migrations, if available.
- `SECRET_KEY` — a strong secret generated or configured in Render.
- `DEBUG=false`.
- `WEB_CONCURRENCY=1` for the current service configuration.

Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` if a custom domain is used. Render's service hostname is added to the trusted host and CSRF origin settings automatically.

After deployment, verify `/healthz`, the public website, login, logout, each role's dashboard summary, password change, the Django administration site and the retained legacy management screens. Review deployment logs and confirm migrations completed successfully.

## 9. Security and privacy requirements

- Enforce role permissions on the Django backend and API.
- Use Django session authentication; do not store authentication tokens in browser local storage.
- Require CSRF tokens for state-changing API requests.
- Keep session cookies HTTP-only and secure in production.
- Apply rate limiting to API login attempts.
- Keep secrets in environment variables and out of Git.
- Do not expose raw biometric data in URLs, logs or client-side storage.
- Do not collect or store facial images or biometric templates until institutional privacy, retention, encryption, access-control and deletion requirements are approved and implemented.
- Preserve academic and attendance history through protected relationships and controlled deactivation.

## 10. Release conventions

Every RollNexa update must follow these project rules:

1. Every release must include a clear GitHub commit message.
2. All code must use four spaces per indentation level. Do not mix tabs and spaces.
3. `README.md` is the only Markdown file permitted in the repository unless the project owner explicitly approves another Markdown file.
4. `README.md` contains the software description and the guide for running the software locally.
5. Extend the existing application. Do not replace working functionality or reset production data without explicit approval.
6. Each release must include source validation and the relevant backend and frontend test results. Do not describe checks as passed if they were not executed.

### Version 0.7.0 GitHub commit message

```text
Introduce React frontend and Django REST API for RollNexa 0.7.0
```

## 11. Development roadmap

| Release | Objective |
| --- | --- |
| 0.7.0 | React foundation, public website, session-authenticated API and dashboard shell. |
| 0.8.0 | Complete administrator, lecturer and student dashboards and migrate existing management workflows to React. |
| 0.9.0 | Secure dynamic QR Code generation, scanning, token expiry and server-side validation. |
| 1.0.0 | Facial enrolment, facial recognition, liveness safeguards, integrated attendance verification and comprehensive testing. |

The roadmap is a development plan. A feature becomes operational only after implementation, testing and deployment in the corresponding release.
