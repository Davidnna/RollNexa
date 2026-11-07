# RollNexa

**Attendance, connected.**

RollNexa is a web-based Smart Academic Attendance Platform prototype. Its planned workflow connects academic users, attendance sessions, identity verification and institutional attendance records.

## Current release: 0.2.1 — Brand refresh

This release rebrands AttendIQ as RollNexa and updates the logo, favicon, colour palette, interface copy, metadata and deployment naming. It preserves the existing 0.2.0 user-management functionality.

### Current functionality
- Django authentication and session management
- Administrator, lecturer and student roles
- Administrator-created student and lecturer accounts
- Temporary passwords with mandatory change at first sign-in
- Account activation and deactivation
- Role-specific dashboards
- Neon PostgreSQL persistence
- Render deployment with automatic deploys from GitHub

### Planned modules
- Faculties, departments, programmes and course management
- Lecturer-course assignment
- QR-code attendance sessions and verification
- Facial enrollment and identity verification
- Attendance records, analytics and exports

Do not describe planned modules as already implemented.

## Hosting architecture
- **GitHub:** source repository (`Davidnna/RollNexa` after repository rename)
- **Render:** Django web application
- **Neon:** managed PostgreSQL database

The application uses `DATABASE_URL` (Neon pooled connection) and `DIRECT_DATABASE_URL` (Neon direct connection for migrations). Never commit these credentials.

## Rebranding an existing deployment
This is an in-place branding release. Do not create a new Render service or a new Neon database.

1. In Render, open the existing AttendIQ web service and rename that same service to `rollnexa` in its Settings. Confirm the target `rollnexa.onrender.com` is available. Do not click **New Web Service**.
2. If the Render Blueprint sync preview proposes creating a second web service rather than updating the existing one, cancel the sync and resolve the service-name mapping before continuing.
3. Upload the extracted RollNexa package contents to the existing GitHub repository `https://github.com/Davidnna/AttendIQ`, replacing files at the repository root.
4. Commit with: `Rebrand AttendIQ as RollNexa 0.2.1`.
5. Allow the existing Render service to deploy. The updated `render.yaml` uses the service name `rollnexa` to match the renamed service.
6. Verify the new brand at the service URL, `/healthz`, login and role dashboards.
7. After successful deployment, rename the GitHub repository from `AttendIQ` to `RollNexa` using **Repository → Settings → General → Repository name**. GitHub redirects most web and Git operations from the previous repository URL, but update future references to `https://github.com/Davidnna/RollNexa`.

If `rollnexa.onrender.com` is unavailable, stop before changing the service name and choose another brand-consistent Render service slug. Do not create a duplicate service.

## Database and migration safety
This release makes **no database schema changes and runs no new migrations**. It does not change the Neon database, database credentials, existing accounts, passwords, roles or user records. Do not reset or recreate the database.

Keep the following existing Render environment variables unchanged:
- `DATABASE_URL`
- `DIRECT_DATABASE_URL`
- `SECRET_KEY`
- `DEBUG`
- `PYTHON_VERSION`
- `WEB_CONCURRENCY`
- `BOOTSTRAP_ADMIN_TOKEN` (if it is still present for initial setup; normally remove it after the first administrator has been created)

## Files and branding
- `BRAND_GUIDELINES.md` contains the RollNexa visual and verbal identity.
- `static/images/rollnexa-logo.svg` is the horizontal logo.
- `static/images/rollnexa-mark.svg` is the standalone mark.
- `static/images/favicon.svg` is the browser icon.

## Security
- Never commit `.env`, database URLs, passwords, API keys, bootstrap tokens or biometric information.
- Do not use real student or biometric data until privacy, security, retention, access and backup arrangements have been established.
- The temporary administrator bootstrap token must be removed from Render after the first administrator is created.
