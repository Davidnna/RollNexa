# RollNexa 1.0.0

**Academic management and dual-verification attendance.**

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

The model assets are downloaded during the Docker image build by `biometrics/download_models.py`. The downloader checks each model's SHA-256 digest and validates that OpenCV can load both models. The ONNX model binaries are not committed to the application repository. Their upstream license notices are downloaded beside the models in the image.

### Enrolment

- The student must review the biometric notice and explicitly grant consent before enrolment.
- Enrolment captures three frames in order: neutral, slight left turn and slight right turn. The server checks the requested pose changes and that the captures represent a consistent identity.
- The server creates a normalised facial feature vector and encrypts it before storage.
- The application stores the encrypted feature template, model/version metadata and enrolment timestamps. It does not persist the captured enrolment images.
- Only one active face template is retained for each student profile.

### Attendance verification

- The server requires exactly one detectable face in each frame.
- Images must be valid, at least 320 by 240 pixels, no more than four million pixels and no larger than 2 MB per frame.
- Both the neutral and challenge frames must match the enrolled template and one another above the configured cosine threshold.
- A randomised left/right head-turn instruction is checked using the change in the detected nose-to-eye landmark ratio.
- Captured attendance frames are processed in memory and are not written as image files by the application.
- The audit record stores the outcome, failure code, liveness-check outcome and model version, not the captured images or similarity score.

**Liveness limitation:** The current head-turn check is a basic challenge-response pose heuristic. It is not a certified presentation-attack-detection (PAD) system and must not be described as proof against sophisticated photo, screen replay, deepfake or camera-injection attacks. A production institution requiring stronger anti-spoofing assurance should independently evaluate and integrate a dedicated PAD model or supervised capture procedure.

### Matching threshold

The default cosine similarity threshold is `0.363`, configurable through `BIOMETRIC_FACE_MATCH_THRESHOLD`. OpenCV documents this value for its SFace/LFW benchmark, while its published thresholds differ across other evaluation datasets. It is an initial engineering default, not a validated threshold for every student population, camera, lighting condition or demographic group. The institution must conduct a representative calibration and false-accept/false-reject evaluation before relying on the system for consequential attendance decisions.

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

The administrator role is represented by Django superuser accounts. Lecturer and student roles are stored on `UserProfile`. Django API views and domain services enforce permissions. Hiding an action in React is not treated as an access-control mechanism.

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
    accounts/              Authentication, profiles, roles and account management
    academics/             Institutional structure, courses, assignments and registration
    api/                   Versioned REST API, workspace endpoints and API tests
    attendance/            Attendance sessions, records, QR and manual exception services
    biometrics/            Consent, enrolment, face processing, challenges and audit records
        migrations/        Biometric database migrations
        model_assets/      Downloaded ONNX model assets and model licence notices
    config/                Django settings and URL configuration
    core/                  Health and shared application views
    frontend/              React, TypeScript, Vite and styles
        src/
            context/       Authentication context
            layouts/       Public and authenticated layouts
            lib/           API client and shared utilities
            pages/         Public pages, dashboards and workspace modules
    static/                Static assets and built React application
    templates/             Legacy Django templates retained during migration
    Dockerfile             Multi-stage React and Django image build
    docker-entrypoint.sh   Database migration and Gunicorn startup
    manage.py              Django management entry point
    requirements.txt       Python dependencies
    render.yaml            Render Blueprint configuration
    build.sh               Local build helper
    VERSION                Current release version
    README.md              Software description and local setup guide
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
- `POST /api/v1/biometrics/enrolment/` — multipart submission of exactly three enrolment frames.
- `DELETE /api/v1/biometrics/enrolment/` — delete the student's stored facial template.
- `POST /api/v1/biometrics/verifications/{verification_id}/challenge/` — issue a single-use randomised head-turn challenge for a pending QR verification.
- `POST /api/v1/biometrics/verifications/{verification_id}/verify/` — multipart submission of the neutral and challenge frames; server-side matching and liveness checks run before the attendance service can record a present entry.

The biometric verification API does not accept a browser-supplied success flag. A successful attendance record is created by the backend service only after the server-side face verification operation succeeds.

## 8. Requirements

- Python 3.12.
- Node.js 22 and npm.
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
python -m pip install -r requirements.txt
```

### 9.2 Configure environment variables

The Django settings read environment variables directly; a `.env` file is not loaded automatically. Set the variables in the terminal or your IDE run configuration.

Linux or macOS example:

```bash
export DEBUG=True
export SECRET_KEY='replace-with-a-long-local-development-secret'
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DATABASE'
export ALLOWED_HOSTS='localhost,127.0.0.1'
export BIOMETRIC_CONSENT_POLICY_VERSION='1.0'
export BIOMETRIC_FACE_MATCH_THRESHOLD='0.363'
export BIOMETRIC_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export BIOMETRIC_ENCRYPTION_KEY_VERSION='v1'
```

Windows PowerShell example:

```powershell
$env:DEBUG = "True"
$env:SECRET_KEY = "replace-with-a-long-local-development-secret"
$env:DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DATABASE"
$env:ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:BIOMETRIC_CONSENT_POLICY_VERSION = "1.0"
$env:BIOMETRIC_FACE_MATCH_THRESHOLD = "0.363"
$env:BIOMETRIC_ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
$env:BIOMETRIC_ENCRYPTION_KEY_VERSION = "v1"
```

Use a dedicated local database. Do not use production database credentials for local development. Keep real secrets out of GitHub and never paste them into source files.

**Important:** Back up the production `BIOMETRIC_ENCRYPTION_KEY` securely. If it is lost or changed, existing encrypted facial templates cannot be decrypted. Key rotation is not automated in this release; do not rotate the key after enrolment without a controlled re-encryption or re-enrolment plan.

### 9.3 Install the face model assets

```bash
python biometrics/download_models.py
```

The script downloads the YuNet and SFace ONNX files, verifies their SHA-256 digests and checks that OpenCV can load them. It also downloads the upstream model licence notices. The models are not committed to Git.

### 9.4 Apply database migrations

```bash
python manage.py check
python manage.py migrate
```

The 1.0.0 migrations add biometric consent, encrypted face enrolment, verification challenges and audit records. They also extend the existing attendance record to distinguish automated dual verification from lecturer-approved manual exceptions. Existing automated attendance rows are migrated as `dual_verified`; the database is not reset.

Create a local administrator if the database does not already have one:

```bash
python manage.py createsuperuser
```

### 9.5 Install and run the React frontend

In a second terminal:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Open the Vite development URL printed by the command, normally `http://localhost:5173`. Vite proxies API requests to Django on `http://127.0.0.1:8000`.

In the first terminal, start Django:

```bash
python manage.py runserver 127.0.0.1:8000
```

For a production-style local build:

```bash
npm --prefix frontend run build
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```

### 9.6 Run tests

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
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
docker build -t rollnexa:1.0.0 .
```

Before deploying to Render:

1. Review the Render Blueprint changes and confirm the service uses the Docker runtime.
2. Ensure `DATABASE_URL`, `DIRECT_DATABASE_URL` where required, `SECRET_KEY` and other existing production settings are configured.
3. Generate a Fernet key using the command in section 9.2 and set it as the secret environment variable `BIOMETRIC_ENCRYPTION_KEY` in Render. Do not commit the value.
4. Set `BIOMETRIC_ENCRYPTION_KEY_VERSION=v1`, `BIOMETRIC_CONSENT_POLICY_VERSION=1.0` and `BIOMETRIC_FACE_MATCH_THRESHOLD=0.363`.
5. Deploy and verify `/healthz`, authentication, database migrations and the biometric status endpoint.
6. Complete controlled enrolment and verification tests before enabling student biometric enrolment institution-wide.

The service can start without a biometric key, but biometric enrolment and matching fail closed until the key is configured. A missing model asset causes the Docker build to fail rather than silently deploying a non-functional facial recogniser.

## 11. Operational and security notes

- Keep the production database and biometric encryption key backed up under separate access controls.
- Restrict access to Render environment settings, database administration and deployment credentials.
- Use HTTPS for all production camera capture and API requests.
- Do not enable biometric collection until the institution approves the privacy notice, lawful basis, DPIA, retention schedule and manual alternative procedure.
- Calibrate the face-match threshold using representative, consented test data and measure false-accept and false-reject rates before operational use.
- Test camera access, lighting, pose, different supported devices and accessibility scenarios.
- Review manual exceptions and failed verification attempts through appropriate institutional audit processes.
- Establish a retention and deletion schedule for biometric consent events and verification audit records; this release records them but does not implement an automatic scheduled purge.
- The QR rotation window reduces the useful life of a copied code but does not prove physical proximity. The face challenge is an additional identity check, not a certified anti-spoofing guarantee.

## 12. Third-party model attribution

- **YuNet face detector** — OpenCV Zoo `face_detection_yunet_2023mar.onnx`; MIT License. Model file SHA-256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
- **SFace face recogniser** — OpenCV Zoo `face_recognition_sface_2021dec.onnx`; Apache License 2.0. Model file SHA-256: `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79`.
- **OpenCV** — Python headless distribution, version pinned in `requirements.txt`.
- **NumPy** and **cryptography** — dependencies pinned by the backend requirements.

The model downloader stores the corresponding upstream `LICENSE` texts beside the downloaded model files. Model references: [YuNet model and MIT notice](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet), [SFace model and Apache 2.0 notice](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface), and [OpenCV DNN face detection and recognition documentation](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html).

## 13. Release conventions

Every RollNexa update must:

- Include a clear GitHub commit message.
- Use four spaces per indentation level in source code; do not mix tabs and spaces.
- Keep exactly one Markdown file in the repository: `README.md`.
- Preserve existing functionality and database records.
- Include migrations for model changes and avoid destructive database resets.
- Be checked before production deployment.
