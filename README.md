# RollNexa 1.1.6

**Academic management and dual-verification attendance.**

Version 1.1.6 corrects the student programme validation test to pass the bound form from the response context to Django's `assertFormError()` API. Version 1.1.5 fixes course CSV import transaction handling. Version 1.1.4 improved CI reliability and test isolation: it collects the WhiteNoise static manifest before template tests, corrects the API test setup for expired QR tokens, explicitly rejects JSON-only face-verification attempts with a validation response, tests biometric key validation using a structurally valid enrolment request, and closes per-thread PostgreSQL connections after concurrency tests. It also orders lecturer attendance sessions deterministically and upgrades GitHub Actions to Node.js 24-compatible releases. Version 1.1.2 adds hosted GitHub Actions workflows for continuous integration, production smoke checks and a manually approved PostgreSQL backup/restore drill. Version 1.1.1 introduced the validation tooling for the 1.1.0 system-hardening release. It adds PostgreSQL concurrency tests, a guarded backup-and-restore verification script, and a management command that checks encrypted facial-template recovery without exposing biometric feature data. It also adds the documented local environment example and strengthens the k6 QR concurrency harness. Version 1.1.3 adds the non-destructive `academics.0008` migration to align Django migration state with the current course metadata and lecturer-assignment ordering. It does not change stored course values or table structure. The CI PostgreSQL service explicitly disables SSL because its local service container does not offer TLS; production continues to require SSL by default whenever `DEBUG=False`, unless an administrator deliberately overrides `DATABASE_SSL_REQUIRE`.

RollNexa is a web-based academic administration and smart attendance platform. It manages institutional structure, user accounts, academic sessions, courses, course offerings, lecturer assignments and student registrations. Its automated attendance workflow combines a rotating QR Code with server-side facial recognition. An automated present record is created only when both verification stages succeed.

RollNexa also provides a lecturer-approved manual attendance exception for students who do not consent to biometric processing or cannot complete automated verification. Manual exceptions are stored and reported separately from automated dual-verification records.

The public website and authenticated React application are served from the same origin. Django remains responsible for authentication, authorisation, validation, business rules, biometric processing and database operations.

## 1. Features

### Public website

- Home, About, Features, How It Works and Contact pages.
- Privacy and Terms pages that the deploying institution must review and approve.
- Secure sign-in entry point.

### System administrator workspace

- Lecturer and student account management.
- Prominent one-time temporary-password dialog after successful account creation.
- Faculty, department and programme management.
- Academic session and semester management.
- Course catalogue and course offering management.
- Global opening and closing of course registration, with individual offering controls.
- Bulk lecturer assignment across matching programme offerings for the same course, semester and level.
- Institution-wide attendance monitoring and reports.
- Separate counts for automated attendance and manual exceptions.

### Lecturer workspace

- Assigned course offerings and registered-student rosters.
- Attendance session scheduling, activation, closure and cancellation.
- Rotating QR Code display for active sessions.
- Attendance verification counts and session reports.
- Lecturer-approved manual attendance exceptions for registered students when biometric attendance is unavailable or unsuitable.
- Manual exceptions are attributed to the approving lecturer and include a reason and optional notes.

### Student workspace

- Course discovery, registration and withdrawal where registration is open.
- QR Code attendance check-in.
- Biometric consent and facial enrolment settings.
- Facial verification after successful QR verification.
- Attendance history showing whether a record was created by automated dual verification or by a manual exception.
- Profile and account security management.

## 2. Attendance workflow

RollNexa's automated attendance policy is **QR Code AND Facial Recognition**. Neither method can independently create an automated present record.

1. An authorised lecturer schedules and activates an attendance session for an assigned course offering.
2. The lecturer displays the session's rotating QR Code.
3. A registered student scans the QR Code. Django validates the signed token, token expiry, active session, lecturer assignment, student account, programme, level and course registration.
4. A successful scan creates or reuses a pending QR verification attempt. It does not create an attendance record.
5. The student completes a server-generated, short-lived facial challenge. The browser captures a neutral frame and a second frame after the requested head movement.
6. Django detects the face, extracts SFace features, compares both captures with the student's enrolled encrypted template and checks the requested head-pose change.
7. The attendance service creates an automated present record only after server-side facial matching and the challenge check succeed, the QR verification remains valid, and all session and registration checks pass.

QR tokens are signed using Django's signing framework. They are not stored in plaintext. The lecturer display refreshes the token every 30 seconds; a token is valid for up to 60 seconds. A pending QR verification expires after five minutes or at the end of the attendance session, whichever occurs first. A verification challenge is single-use and expires within 90 seconds or when the pending QR verification expires, whichever occurs first. Three failed facial attempts cause the pending verification to be marked failed; the student must scan a current QR Code to start another attempt.

### Manual attendance exception

A student may decline biometric enrolment, withdraw consent or be unable to use the camera or complete recognition. In those cases, the student can ask the lecturer to record a manual attendance exception. The exception:

- Can only be created by an active lecturer assigned to the course offering.
- Can only be recorded for an active, registered student while the attendance session is open.
- Requires a reason and, when `Other` is selected, an explanatory note.
- Is attributed to the approving lecturer.
- Is stored in the same attendance ledger with `recording_method=manual_exception`, no QR or face timestamps, and a separate reason.
- Counts as present in total attendance figures but is not counted as an automated dual-verification record.
- Cannot duplicate another attendance record for the same student and session.

The manual exception is an alternative attendance procedure. It is not represented as successful QR or facial verification.

## 3. Facial recognition and biometric data

### Processing architecture

Camera capture takes place in the student's browser. The browser sends the captured frames to the same-origin Django API over HTTPS. Face detection, feature extraction, template comparison and the head-pose challenge check run on the server. The browser cannot submit a trusted `face_verified=true` value or make the final identity decision.

The implementation uses:

- OpenCV `FaceDetectorYN` with the YuNet 2023mar ONNX model for face detection and five-point landmarks. The OpenCV 4.x DNN implementation receives the actual camera-frame dimensions through `setInputSize`, and SFace aligns detected coordinates against the original frame.
- OpenCV `FaceRecognizerSF` with the SFace ONNX model for feature extraction and matching.
- NumPy for feature-vector normalisation and cosine similarity calculations.
- Fernet authenticated encryption from `cryptography` for stored facial templates.

The model assets are downloaded during the Docker image build by `backend/biometrics/download_models.py`. The downloader checks each model's SHA-256 digest and validates that OpenCV can load both models. The ONNX model binaries are not committed to the application repository. Their upstream license notices are downloaded beside the models in the image.

### Enrolment

- The student must review the current biometric notice and explicitly grant consent before enrolment. This release increments the consent policy to version `1.1` because it introduces repeated live-preview frame processing; students with version `1.0` consent must review and accept the updated notice before continuing.
- During enrolment, the browser sends a compressed camera preview frame to the same-origin Django API approximately every 900 milliseconds. The server runs YuNet detection and returns a face count, positioning box, and transient pose ratio for live guidance.
- The guide reports when no face is visible, multiple faces are present, the face is too small or large, the face is off-centre, or the requested head position has been reached.
- The interface automatically captures three stable frames in order: neutral, slight left turn and slight right turn. Each preview frame is processed in memory and is not stored. The final enrolment request rechecks the three frames, verifies pose changes and identity consistency, then creates the encrypted feature template.
- The server creates a normalised facial feature vector and encrypts it before storage.
- The application stores the encrypted feature template, model/version metadata and enrolment timestamps. It does not persist the captured enrolment images.
- Only one active face template is retained for each student profile.

### Attendance verification

- The server requires exactly one detectable face in each frame.
- Images must be valid, at least 320 by 240 pixels, no more than four million pixels and no larger than 2 MB per frame.
- Both the neutral and challenge frames must match the enrolled template and one another above the configured cosine threshold.
- A randomised left/right head-turn instruction is checked using the change in the detected nose-to-eye landmark ratio.
- Captured attendance frames and live enrolment preview frames are processed in memory and are not written as image files by the application.
- The audit record stores the outcome, failure code, liveness-check outcome and model version, not the captured images or similarity score.

**Liveness limitation:** The current head-turn check is a basic challenge-response pose heuristic. It is not a certified presentation-attack-detection (PAD) system and must not be described as proof against sophisticated photo, screen replay, deepfake or camera-injection attacks. A production institution requiring stronger anti-spoofing assurance should independently evaluate and integrate a dedicated PAD model or supervised capture procedure.

### Matching threshold

The default cosine similarity threshold is `0.363`, configurable through `BIOMETRIC_FACE_MATCH_THRESHOLD`. OpenCV documents this value for its SFace/LFW benchmark, while its published thresholds differ across other evaluation datasets. It is an initial engineering default, not a validated threshold for every student population, camera, lighting condition or demographic group. The institution must conduct a representative calibration and false-accept/false-reject evaluation before relying on the system for consequential attendance decisions.

The YuNet detector confidence threshold is separately configurable through `BIOMETRIC_FACE_DETECTION_THRESHOLD` and defaults to `0.75` in this release. This is a detection setting, not an identity-match threshold. A lower detector threshold can reduce missed detections but may admit weaker candidate boxes; the server still requires one face, minimum image/face dimensions, valid landmarks, SFace consistency and final identity checks. Calibrate this value using representative camera samples before institutional use.

### Consent, withdrawal and alternative access

- Consent is recorded against a versioned notice.
- A student can withdraw consent through Biometric Settings.
- Withdrawal deletes the stored facial template and expires the student's pending QR verification attempts.
- Deleting a template also expires pending QR verification attempts.
- A student who does not enrol or withdraws consent can request a lecturer-approved manual attendance exception.
- Historical attendance records remain in the academic attendance ledger; withdrawing biometric consent does not erase previously recorded attendance.

Biometric data used for unique identification is sensitive personal data. For Nigerian deployments, the institution must assess its obligations under the Nigeria Data Protection Act 2023 and applicable Nigeria Data Protection Commission guidance. Before enabling collection for a real institution, it must determine and document its lawful basis, provide an approved privacy notice, define retention and deletion schedules, conduct a Data Protection Impact Assessment where required, establish access and incident procedures, and obtain appropriate legal or data-protection review. This software documentation is not legal advice and does not replace institutional approval or compliance work.

## 4. Roles and access control

| Role | Main capabilities |
| --- | --- |
| System administrator | Manage accounts, institutional structure, academic periods, courses, offerings, lecturer assignments, registration controls, attendance monitoring and reports. |
| Lecturer | View assigned offerings and rosters, manage attendance sessions, display QR Codes, review records and approve manual exceptions for their assigned offerings. |
| Student | View and register for eligible courses, scan attendance QR Codes, manage biometric consent/enrolment, complete facial verification and review attendance history. |

The administrator role is represented by Django superuser accounts. Lecturer and student roles are stored on `UserProfile`. Django API views and domain services enforce permissions. Hiding an action in React is not treated as an access-control mechanism. Django Administration is diagnostic and read-only for user, academic, attendance and biometric records; account and academic changes must go through the audited application workflows. Group administration is not exposed.

## 5. Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite |
| Styling | Tailwind CSS and project CSS |
| Frontend routing | React Router |
| API state | TanStack React Query |
| QR rendering | `qrcode.react` |
| QR camera scanning | `html5-qrcode` |
| Backend | Python 3.12, Django 5.2 |
| API | Django REST Framework |
| Authentication | Django session authentication and CSRF protection |
| Database | PostgreSQL; production database hosted on Neon |
| Face detection and recognition | OpenCV 4.11 headless, YuNet and SFace ONNX models |
| Numerical processing | NumPy |
| Template encryption | `cryptography` Fernet |
| Application server | Gunicorn |
| Static assets | WhiteNoise |
| Deployment | Docker and Render |

## 6. Project structure

```text
rollnexa/
    backend/                       Django application and all backend resources
        accounts/                  Authentication, profiles, roles and account management
        academics/                 Institutional structure, courses, assignments and registration
        api/                       Versioned REST API, workspace endpoints and API tests
        attendance/                Attendance sessions, records, QR and manual exception services
        biometrics/                Consent, enrolment, face processing and verification
            management/             Biometric restore-verification command
            migrations/            Biometric database migrations
            model_assets/           Downloaded ONNX models and licence notices (not committed)
        config/                    Django settings, ASGI, WSGI and URL configuration
        core/                      Shared health, readiness, security headers and audit ledger
            migrations/            Audit-event database migration
        static/                    Django static assets and built React application
        templates/                 Legacy Django templates still used by backend views
        manage.py                  Django management entry point
        requirements.txt           Python dependencies
        docker-entrypoint.sh       Database migration and Gunicorn startup
        .env.example               Local environment-variable reference
    frontend/                      Complete React application
        src/
            context/               Authentication context
            layouts/               Public and authenticated layouts
            lib/                   API client and shared utilities
            pages/                 Public pages, dashboards and workspace modules
        package.json               Frontend dependencies and scripts
        vite.config.ts             Vite build and development proxy configuration
    Dockerfile                     Multi-stage React and Django image build
    render.yaml                    Render Blueprint configuration
    build.sh                       Local build helper
    scripts/                       k6 load test and guarded PostgreSQL restore drill
    .dockerignore                  Docker build exclusions
    .gitignore                     Git exclusions
    .editorconfig                  Four-space editor and whitespace conventions
    VERSION                        Current release version
    README.md                      Software description and local setup guide
```

## 7. API routes

All API endpoints use the `/api/v1/` prefix and the same-origin Django session. Mutating requests require CSRF protection.

### Authentication and workspace

- `GET /api/v1/csrf/` — initialise the CSRF cookie and return the token.
- `GET /api/v1/auth/session/` — return the current authentication state.
- `POST /api/v1/auth/login/` — authenticate and establish a Django session.
- `POST /api/v1/auth/logout/` — end the current session.
- `POST /api/v1/auth/password-change/` — change the authenticated user's password.
- `GET /api/v1/dashboard/summary/` — role-scoped dashboard summary.
- `GET /readyz` — readiness check for database connectivity and required face-model assets.
- `GET /healthz` — liveness check for the web process.
- `/api/v1/workspace/` — role-protected academic, account, roster, attendance and reporting resources.

### QR attendance

- `GET /api/v1/attendance/sessions/{session_id}/qr/` — lecturer-only short-lived signed QR token issuance.
- `POST /api/v1/attendance/verify-qr/` — student-only QR token verification and pending-attempt creation or reuse.
- `GET /api/v1/attendance/verifications/{verification_id}/` — read the authenticated student's own verification status.
- `GET /api/v1/attendance/sessions/{session_id}/manual-records/` — lecturer-only manual attendance audit list for an assigned session.
- `POST /api/v1/attendance/sessions/{session_id}/manual-records/` — lecturer-only manual attendance exception creation.

### Biometrics

- `GET /api/v1/biometrics/status/` — return the student's consent and enrolment state and server model availability.
- `POST /api/v1/biometrics/consent/` — grant or withdraw versioned biometric consent.
- `POST /api/v1/biometrics/face-preview/` — process one transient camera frame and return live face-count, position, size and pose guidance; requires current student consent and is rate-limited.
- `POST /api/v1/biometrics/enrolment/` — multipart submission of exactly three enrolment frames after live guidance.
- `DELETE /api/v1/biometrics/enrolment/` — delete the student's stored facial template.
- `POST /api/v1/biometrics/verifications/{verification_id}/challenge/` — issue a single-use randomised head-turn challenge for a pending QR verification.
- `POST /api/v1/biometrics/verifications/{verification_id}/verify/` — multipart submission of the neutral and challenge frames; server-side matching and liveness checks run before the attendance service can record a present entry.

The biometric verification API does not accept a browser-supplied success flag. A successful attendance record is created by the backend service only after the server-side face verification operation succeeds. The live preview endpoint does not create templates or attendance records; it returns transient positioning feedback and does not persist preview images.

## 8. Requirements

- Python 3.12.
- Node.js 22.12 or later and npm.
- PostgreSQL 14 or later.
- Docker for container builds and production-style local testing.
- A webcam or phone camera for biometric enrolment and attendance verification.
- A secure HTTPS origin for browser camera access outside localhost.
- Internet access during model installation and the Docker build, to download and verify the ONNX model assets and their licence notices.

## 9. Local development setup

### 9.1 Obtain the source and create a Python environment

```bash
git clone YOUR_ROLLNEXA_REPOSITORY_URL
cd rollnexa
python -m venv .venv
```

Activate the environment:

```bash
# Linux or macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 9.2 Configure environment variables

The backend environment-variable reference is `backend/.env.example`. Django settings read environment variables directly; a `.env` file is not loaded automatically. Set the variables in the terminal or your IDE run configuration.

Linux or macOS example:

```bash
export DEBUG=True
export SECRET_KEY='replace-with-a-long-local-development-secret'
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DATABASE'
export ALLOWED_HOSTS='localhost,127.0.0.1'
export BIOMETRIC_CONSENT_POLICY_VERSION='1.1'
export BIOMETRIC_FACE_MATCH_THRESHOLD='0.363'
export BIOMETRIC_FACE_DETECTION_THRESHOLD='0.75'
export BIOMETRIC_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export BIOMETRIC_ENCRYPTION_KEY_VERSION='v1'
```

Windows PowerShell example:

```powershell
$env:DEBUG = "True"
$env:SECRET_KEY = "replace-with-a-long-local-development-secret"
$env:DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DATABASE"
$env:ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:BIOMETRIC_CONSENT_POLICY_VERSION = "1.1"
$env:BIOMETRIC_FACE_MATCH_THRESHOLD = "0.363"
$env:BIOMETRIC_FACE_DETECTION_THRESHOLD = "0.75"
$env:BIOMETRIC_ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
$env:BIOMETRIC_ENCRYPTION_KEY_VERSION = "v1"
```

Use a dedicated local database. Do not use production database credentials for local development. Keep real secrets out of GitHub and never paste them into source files.

**Important:** Back up the production `BIOMETRIC_ENCRYPTION_KEY` securely. If it is lost or changed, existing encrypted facial templates cannot be decrypted. Key rotation is not automated in this release; do not rotate the key after enrolment without a controlled re-encryption or re-enrolment plan.

### 9.3 Install the face model assets

```bash
python backend/biometrics/download_models.py
```

The script downloads the YuNet and SFace ONNX files, verifies their SHA-256 digests and checks that OpenCV can load them. It also downloads the upstream model licence notices. The models are not committed to Git.

### 9.4 Apply database migrations

Run Django management commands from the `backend/` directory:

```bash
(
    cd backend
    python manage.py check
    python manage.py migrate
)
```

Apply all pending migrations, including `academics.0008_alter_courselecturerassignment_options_and_more` and `core.0001_initial`. The academic migration aligns model metadata without rewriting course records or changing table structure; the core migration creates the audit-event ledger. The attendance migrations distinguish automated dual verification from lecturer-approved manual exceptions. Existing automated attendance rows are migrated as `dual_verified`; the database is not reset.

Create a local administrator if the database does not already have one:

```bash
(
    cd backend
    python manage.py createsuperuser
)
```

### 9.5 Install and run the React frontend

In the first terminal, from the repository root, start Django from `backend/`:

```bash
cd backend
python manage.py runserver 127.0.0.1:8000
```

In a second terminal, from the repository root, install and start React:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Open the Vite development URL printed by the command, normally `http://localhost:5173`. Vite proxies API requests to Django on `http://127.0.0.1:8000`.

For a production-style local build, run these commands from the repository root:

```bash
npm --prefix frontend run build
(
    cd backend
    python manage.py collectstatic --noinput
    python manage.py runserver 127.0.0.1:8000
)
```

### 9.6 Run tests

```bash
(
    cd backend
    python manage.py check
    python manage.py makemigrations --check --dry-run
    python manage.py test
)
```

Frontend checks:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## 10. Docker and Render deployment

The Dockerfile builds the React application, installs Python dependencies, downloads and validates the ONNX models and licence notices, collects static files and starts Gunicorn. The container entrypoint applies database migrations before starting the application.

Build locally:

```bash
docker build -t rollnexa:1.1.5 .
```

Before deploying to Render:

1. Review the Render Blueprint changes and confirm the service uses the Docker runtime.
2. Ensure `DATABASE_URL`, `DIRECT_DATABASE_URL` where required, `SECRET_KEY` and other existing production settings are configured.
3. Set `BIOMETRIC_ENCRYPTION_KEY` in Render. The Blueprint uses `generateValue: true`, which asks Render to create a Base64-encoded 256-bit secret compatible with Fernet. Render generates this value only when the variable does not already exist; syncing the Blueprint does not replace an existing value. If the application reports an invalid key and no facial templates have ever been successfully enrolled, replace the existing value using Render's **Generate Random Value** option and redeploy. If any templates have been enrolled, do not replace the key; use a controlled key migration. For local development, generate a Fernet key with the command in section 9.2. Do not commit the value.
4. Set `BIOMETRIC_ENCRYPTION_KEY_VERSION=v1`, `BIOMETRIC_CONSENT_POLICY_VERSION=1.1`, `BIOMETRIC_FACE_MATCH_THRESHOLD=0.363` and `BIOMETRIC_FACE_DETECTION_THRESHOLD=0.75`.
5. Confirm the Blueprint applies `SECURE_SSL_REDIRECT=true` and `SECURE_HSTS_SECONDS=31536000`. Production database SSL remains required by default when `DEBUG=False`; `DATABASE_SSL_REQUIRE` exists for explicit environment-specific overrides and is set to `false` only for the ephemeral, non-TLS PostgreSQL service used by GitHub CI. The readiness endpoint is exempt from redirects so Render can probe it over the service network.
6. If using a custom domain, add it to `ALLOWED_HOSTS` and add its HTTPS origin to `CSRF_TRUSTED_ORIGINS`.
7. Deploy and verify `/healthz`, `/readyz`, HTTPS redirects, HSTS, authentication, database migrations and the biometric status endpoint.
8. Complete controlled enrolment and verification tests before enabling student biometric enrolment institution-wide.

The service can start without a biometric key, but biometric enrolment and matching fail closed until the key is configured. A missing model asset causes the Docker build to fail rather than silently deploying a non-functional facial recogniser.

## 11. Operational and security notes

### Audit ledger

The `core.AuditEvent` table is an append-only event ledger. System administrators can review it in Django Administration under **Audit events**. The actor's username is retained as a snapshot if the user account is later removed. Event metadata is intentionally limited to operational identifiers and state changes; it must never contain passwords, session/QR tokens, encryption keys, camera frames, facial templates, embeddings or free-text notes. Application model saves reject updates to existing audit-event rows, and Django Administration does not expose add, change or delete actions. User, group, academic, attendance and biometric records are read-only in Django Administration so mutations use the application workflows that emit audit events. Database owners can still alter data directly, so database access remains privileged and must be audited by the hosting provider.

### Production checks

Run the backend tests and deployment checks from `backend/`:

```bash
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
```

Run the frontend checks from the repository root:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Build the container with `docker build -t rollnexa:1.1.5 .`. The repository currently pins direct frontend dependencies in `frontend/package.json` but does not include a generated `package-lock.json`; generate and commit one through the hosted CI artifact or a network-enabled dependency-resolution environment to make transitive frontend dependency resolution reproducible.

- Keep the production database and biometric encryption key backed up under separate access controls.
- Production defaults enforce HTTPS redirects and one-year HSTS. `/healthz` and `/readyz` are exempt from Django's redirect so Render health probes can reach them; the application routes are not exempt.
- The React application receives a Content Security Policy that permits same-origin scripts and API calls, the Google Fonts hosts used by the interface, and camera media streams. A Permissions Policy allows camera access only to the same origin and disables microphone and geolocation access.
- Biometric multipart requests are limited to 8 MB at the request boundary, no more than three uploaded files, 2 MB per image, and the image dimensions are inspected from the JPEG header before OpenCV decodes the image. Camera images are expected to be JPEGs generated by the frontend.
- Security- and operations-relevant actions are written to the read-only **Audit events** section in Django Administration. Events cover account lifecycle and password changes, academic and course-registration changes, lecturer assignments, attendance-session lifecycle, QR check-ins, automated and manual attendance records, biometric consent, enrolment and verification outcomes. Audit metadata is filtered to exclude passwords, tokens, secrets, image/frame data, templates, embeddings, cookies, credentials and free-text notes.
- DRF login, QR and biometric endpoints use scoped throttles. The default Django cache is process-local; the current Render Blueprint uses one Gunicorn worker. Before adding workers or service instances, configure a shared cache such as Redis and edge-level rate limiting so limits cannot be bypassed by spreading requests across processes. Django Administration login is separate from the DRF login throttle; restrict administrator access at the hosting/identity layer and require strong unique administrator credentials. Multi-factor authentication is not implemented in this application release.
- For a custom domain, include the hostname in `ALLOWED_HOSTS` and its HTTPS origin in `CSRF_TRUSTED_ORIGINS`. The Render-provided hostname is added automatically.
- Audit events are append-only through the application and read-only in Django Administration. The institution must define and implement its own retention schedule; the application does not automatically purge audit events or biometric consent/verification history.
- Restrict access to Render environment settings, database administration and deployment credentials.
- Use HTTPS for all production camera capture and API requests.
- Do not enable biometric collection until the institution approves the privacy notice, lawful basis, DPIA, retention schedule and manual alternative procedure.
- Calibrate the face-match threshold using representative, consented test data and measure false-accept and false-reject rates before operational use.
- Test camera access, lighting, pose, different supported devices and accessibility scenarios.
- Review manual exceptions and failed verification attempts through appropriate institutional audit processes.
- Establish a retention and deletion schedule for biometric consent events, biometric verification attempts and general audit events. The audit ledger records changes but does not implement an automatic scheduled purge.
- The QR rotation window reduces the useful life of a copied code but does not prove physical proximity. The face challenge is an additional identity check, not a certified anti-spoofing guarantee.

### Concurrent QR check-in test

A k6 script is included at `scripts/k6_qr_checkin.js`. It supports two controlled modes, each limited to eight virtual users to stay within the current login and QR API throttles:

- `MODE=distinct`: use one clean test-student account per virtual user. Each student must be active, registered for the session's course offering and not already marked present or holding a pending verification. The expected result is one new pending verification per student.
- `MODE=same-student`: use one clean test-student account across all virtual users. The expected result is exactly one new pending verification and all other simultaneous requests reusing that same pending attempt. This exercises the QR check-in idempotency and session-row serialization.

Create a temporary JSON file at `scripts/students.test.json` containing an array of `{ "username": "...", "password": "..." }` test accounts, and save a freshly issued QR token to `scripts/qr-token.txt`. In `same-student` mode the JSON array must contain exactly one account; in `distinct` mode it must contain exactly as many accounts as the requested concurrency. These paths are excluded from Git. Restrict their local permissions and never use real student credentials.

Run only against an isolated staging deployment with test students and a test attendance session. The QR token has a short validity window, so run immediately after the lecturer activates the session and issues a fresh token:

```bash
chmod 600 scripts/students.test.json scripts/qr-token.txt
export BASE_URL="https://your-staging-rollnexa-domain"
export STUDENTS_JSON="$(cat scripts/students.test.json)"
export QR_TOKEN="$(cat scripts/qr-token.txt)"
export MODE="same-student"
export CONCURRENCY="8"
k6 run scripts/k6_qr_checkin.js
unset STUDENTS_JSON QR_TOKEN
```

For `distinct` mode, set `MODE=distinct` and provide eight distinct accounts. The script enforces successful checks, zero failed HTTP requests, a five-second p95 QR response target, and the expected counts of newly created versus reused pending verifications. It deliberately stops at `qr_verified`; it does not simulate facial verification or create attendance records. PostgreSQL `TransactionTestCase` coverage separately exercises simultaneous QR scans and simultaneous completion of the server-side dual-verification service. Neither the k6 test nor the Django concurrency tests should be described as executed until their actual results have been captured.

### Backup and restore drill

Create a PostgreSQL custom-format backup using the direct database connection string. Keep the dump outside GitHub and protect it with the institution's approved storage encryption and access controls:

```bash
pg_dump --format=custom --no-owner --no-acl "$DIRECT_DATABASE_URL" --file="rollnexa-backup.dump"
pg_restore --list "rollnexa-backup.dump"
```

Restore only into an isolated staging database, never over production. Do not use `pg_restore --clean` or `--if-exists` for a recovery drill because those options can drop existing objects in the target. Use the guarded script below, which requires a newly created empty staging database and refuses to target the source database.

After restoring, run Django checks and verify account, course, registration and attendance counts against the backup manifest. If biometric templates exist, configure the matching backed-up `BIOMETRIC_ENCRYPTION_KEY` and key version in the isolated staging service, then verify that every stored template can be decrypted without displaying or exporting feature vectors. Database backups and the biometric encryption key must be recoverable together; a database-only restore cannot recover facial matching if the key has been lost. Record the date and outcome of each restore drill.

For a repeatable drill, `scripts/verify_postgres_restore.sh` automates the archive, empty-target, row-count, migration-state and biometric-template checks. It requires `SOURCE_DATABASE_URL` to point to the direct source database and `STAGING_DATABASE_URL` to point to a separate, newly created empty database. Set `SOURCE_DATABASE_URL` from the protected `DIRECT_DATABASE_URL` setting without printing or committing either value. The script deliberately refuses to restore into a non-empty target or the same database identity. Run it only from a secured operations environment with PostgreSQL client tools and the backend Python dependencies installed. Perform the comparison during a controlled maintenance window so concurrent production writes do not change row counts during the drill. The original biometric key and key version must be present in that environment; never put them in source files or logs.

The `python manage.py verify_biometric_restore` command can also be run independently against a restored database. It decrypts templates in memory and reports only aggregate success/failure counts.

## 12. Hardening status and residual validation


### Hosted validation workflows (version 1.1.2–1.1.5)

The repository includes three GitHub Actions workflows under `.github/workflows/`:

- `ci.yml` runs Django checks and the full test suite against an ephemeral PostgreSQL 16 service, checks migrations, builds the React application and builds the production Docker image without publishing it. The ephemeral service sets `DATABASE_SSL_REQUIRE=false`; this is isolated to CI and does not change the production SSL default. The frontend job resolves dependencies, creates a `package-lock.json`, uploads it as a short-lived workflow artifact and uses that exact lockfile for `npm ci`. The Docker build job independently generates a lockfile in its checked-out build context so the Dockerfile can use `npm ci` during that image build. The generated lockfile must still be added to the repository to make subsequent installs reproducible.
- `production-smoke.yml` can be triggered manually to check the deployed `/healthz` and `/readyz` endpoints and verify the expected HTTPS security headers on `https://rollnexa.onrender.com`.
- `backup-restore-drill.yml` is manually triggered from `main` and requires the exact confirmation text `RESTORE_TO_ISOLATED_STAGING`. Configure the protected GitHub Actions repository secrets `SOURCE_DATABASE_URL`, `STAGING_DATABASE_URL`, `BIOMETRIC_ENCRYPTION_KEY` and `BIOMETRIC_ENCRYPTION_KEY_VERSION` before using it. The staging database must be newly created and empty. The workflow never uploads the database dump as an artifact and deletes the temporary dump when the job finishes.

The backup/restore workflow is intentionally manual because it reads production data and writes to a staging database. Run it during a controlled maintenance window, keep the source and staging databases separate, and ensure the original biometric encryption key is available through protected secrets. Do not enable automatic execution for this workflow.

These workflows are included as source configuration only. Their presence does not mean they have executed. A successful GitHub Actions run is required before reporting CI, production smoke checks, backup restoration or hosted concurrency tests as passed.

### Application hardening introduced in version 1.1.0

- HTTPS redirects and one-year HSTS are enabled by the Render Blueprint; health probes use separate liveness and readiness endpoints.
- The React application receives a restrictive Content Security Policy and a same-origin camera Permissions Policy. Session and CSRF cookies are secure, HttpOnly and SameSite=Lax in production.
- User, academic, attendance and biometric records are read-only in Django Administration. Application changes use role-protected workflows and write append-only audit events.
- Biometric multipart request size, file count and per-image size are bounded. JPEG dimensions are checked before OpenCV image decoding.
- Facial challenge issuance locks the session and verification in a consistent order. Attendance recording remains transactional and requires the server-side QR and face verification states.
- The k6 harness supports distinct-student and same-student QR check-in races, with strict result-count and request-success thresholds. PostgreSQL-specific `TransactionTestCase` tests exercise simultaneous QR scans and simultaneous final attendance completion.

### Validation tooling added in version 1.1.1

- `backend/biometrics/management/commands/verify_biometric_restore.py` checks that the configured key version matches and decrypts every stored facial template. It reports aggregate counts only; it never prints, serializes or exports feature vectors.
- `scripts/verify_postgres_restore.sh` creates a custom-format backup, verifies archive readability, refuses to restore into a non-empty or identical source database, restores into an isolated empty staging database, compares public-table row counts, checks migration state and invokes the biometric-template recovery command.
- PostgreSQL-only `TransactionTestCase` tests use independent database connections to race simultaneous QR scans and simultaneous dual-verification completion.
- The k6 script now supports both distinct-student load and same-student duplicate-scan races, and enforces exact new-versus-reused pending-verification counts.
- `backend/.env.example` now exists and documents local-only environment settings without containing production secrets.

### Migration and database SSL configuration (version 1.1.3)

- `academics.0008_alter_courselecturerassignment_options_and_more` records the current lecturer-assignment ordering and the current `Course.credit_units` and `Course.stress_code` help text in migration state. These are metadata/state changes only; no data rewrite or destructive schema operation is performed.
- `DATABASE_SSL_REQUIRE` optionally overrides the database TLS requirement. If omitted, the default remains `not DEBUG`, so production (`DEBUG=False`) requires SSL. The GitHub Actions PostgreSQL service explicitly sets it to `false` because the service container is local and does not support TLS. Never copy this CI override into the production Render environment.

### CI and test reliability (versions 1.1.4–1.1.5)

- The CI workflow runs `python manage.py collectstatic --noinput` before the Django test suite. This creates the WhiteNoise manifest used by `{% static %}` in templates and mirrors the production Docker build, which already collects static assets.
- The expired-QR API test now uses DRF's `APIClient.force_authenticate` so it tests the expired-token response rather than failing first on SessionAuthentication's CSRF requirement. The separate API security tests continue to exercise CSRF enforcement.
- The face-verification endpoint also parses JSON so a JSON-only request (including a client-supplied `faceVerified` boolean) receives an explicit HTTP 400 validation response. Actual verification still requires the server challenge and two uploaded frames.
- The invalid-encryption-key enrolment test submits exactly three frames so request-shape validation passes and the test reaches the intended fail-closed key-configuration check before any face processing.
- Concurrency-test worker threads now close all of their own Django database connections. This prevents healthy persistent connections from remaining attached to worker threads and blocking PostgreSQL test-database deletion.
- Lecturer attendance-session pagination now has a stable `starts_at`/primary-key ordering.
- GitHub Actions dependencies have been updated to Node.js 24-compatible major releases.

The last available hosted run (`45115749357`) passed migration checks and the React production build. Its Django run executed 192 tests but was blocked by 52 template errors caused by the uncollected static manifest, three independent test failures, and four lingering PostgreSQL connections during test-database teardown. Version 1.1.4 addresses those findings. A new hosted run is still required to confirm that the corrections pass together; this package has not been represented as having a successful post-fix CI run.

### Must still be validated in the deployment environment

- Re-run the complete hosted PostgreSQL CI workflow against this release. The preparation environment does not contain Django or PostgreSQL, so post-fix runtime tests and migration execution have not been performed locally. The previous hosted run is diagnostic evidence only and does not validate this revision.
- The previous hosted run completed the Vite production build and generated a short-lived `package-lock.json` artifact. The Docker image job was skipped because the backend job failed. Commit a reviewed `frontend/package-lock.json` when the hosted artifact is adopted so transitive dependency resolution is reproducible.
- Execute the PostgreSQL-specific concurrency tests and run both k6 modes against a staging deployment. Perform the restore drill using `scripts/verify_postgres_restore.sh` with a real direct production connection and a newly provisioned, empty staging database. The staging environment must receive the original `BIOMETRIC_ENCRYPTION_KEY` and matching key version through secure environment configuration before the restore verification command can validate templates.
- Measure false-accept and false-reject rates using a representative, consented evaluation set. The SFace threshold `0.363` is a published benchmark reference, not a RollNexa-specific calibrated threshold.
- The randomised head-turn challenge is a heuristic liveness check, not a certified presentation-attack detection system. It must not be represented as proof that sophisticated photo, screen or video replay attacks are impossible. Retain the lecturer-approved manual alternative and evaluate a dedicated PAD model before high-stakes deployment.
- The DRF throttles use Django's process-local cache. Configure shared cache and edge rate limiting before scaling beyond the current single-worker/single-instance configuration. Django Administration does not have built-in MFA in this release; protect administrator access with the institution's identity and network controls.
- The institution must approve the privacy notice, lawful basis, DPIA, biometric retention schedule, audit retention schedule and incident-response process before collecting real student biometric data.

A successful container build and application smoke test are necessary but do not replace the accuracy, security, privacy, backup/restore and load evaluations listed above.

## 13. Third-party model attribution

- **YuNet face detector** — OpenCV Zoo `face_detection_yunet_2023mar.onnx`; MIT License. Model file SHA-256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
- **SFace face recogniser** — OpenCV Zoo `face_recognition_sface_2021dec.onnx`; Apache License 2.0. Model file SHA-256: `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79`.
- **OpenCV** — Python headless distribution, version pinned in `backend/requirements.txt`.
- **NumPy** and **cryptography** — dependencies constrained to supported version ranges in the backend requirements.

The model downloader stores the corresponding upstream `LICENSE` texts beside the downloaded model files. Model references: [YuNet model and MIT notice](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet), [SFace model and Apache 2.0 notice](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface), and [OpenCV DNN face detection and recognition documentation](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html).

## 14. Repository structure and release conventions

The repository separates application source by responsibility: all Django code, templates, static assets and Python dependencies live in `backend/`; all React, TypeScript, Vite and frontend dependencies live in `frontend/`. Root-level files are limited to repository documentation, version metadata, editor settings and deployment/build orchestration.

`.editorconfig` defines four spaces per indentation level (`indent_size=4`, `tab_width=4`) and LF line endings. Use spaces rather than literal tab characters so formatting remains consistent across Python, TypeScript, TSX, CSS, HTML, JSON and YAML.

Every RollNexa update must:

- Include a clear GitHub commit message.
- Use four spaces per indentation level in source code; do not mix tabs and spaces.
- Keep exactly one Markdown file in the repository: `README.md`.
- Preserve existing functionality and database records.
- Include migrations for model changes and avoid destructive database resets.
- Be checked before production deployment.


### Version 1.1.5 — CSV import and test assertion fixes

The 1.1.4 hosted test run executed all 192 Django tests and identified four errors in course CSV import tests. The common root cause was that `apply_course_import_plan()` used `transaction.atomic()` without importing `transaction` from `django.db`. Version 1.1.5 adds that import; the four course-import errors share this single root cause.

The same run identified one failing account-creation test. The rendered page already displayed the correct programme validation error, but the test searched the raw HTML for an apostrophe that Django correctly HTML-escaped as `&#x27;`. Version 1.1.5 changes the assertion to `assertFormError()` so it checks the actual form-field error rather than the HTML serialization. No application validation behaviour or user-facing wording was changed.

No database migration is required. These changes must be confirmed by a new hosted run of `python manage.py test --verbosity=2`.
