# RollNexa

**Attendance, connected.**

RollNexa is a web-based Smart Academic Attendance Platform prototype. Its planned workflow connects academic users, attendance sessions, identity verification and institutional attendance records.

## Current release: 0.3.0 — Academic Structure Management

This release adds institutional academic structures and academic-calendar management to the existing authentication and role-based account system.

### Current functionality
- Django authentication and session management
- System administrator, lecturer and student roles
- Administrator-created student and lecturer accounts
- Temporary passwords with mandatory change at first sign-in
- Account activation and deactivation
- Role-specific dashboards
- Faculty, department and programme management
- Academic session and semester management
- One current academic session and one current semester, with parent-child validation
- Student programme/level and lecturer department assignments
- Editing existing accounts to add or update academic assignments
- Soft deactivation of academic records to preserve historical relationships
- Neon PostgreSQL persistence
- Render deployment with automatic deploys from GitHub

### Planned modules
- Course catalogue and course offerings
- Lecturer-course allocation and student course registration
- QR-code attendance sessions and verification
- Facial enrollment and identity verification
- Attendance records, analytics and exports

Do not describe planned modules as already implemented.

## Academic data model
- A faculty contains departments.
- A department belongs to one faculty and contains programmes.
- A student profile may be assigned to a programme and current level. The student's department is derived from that programme.
- A lecturer profile may be assigned to a department.
- An academic session contains semesters. Only one session can be current at a time, and only one semester can be current at a time. A current semester must belong to the current session.
- Academic records are deactivated rather than deleted. Deactivating a faculty also deactivates its departments and programmes; deactivating a department deactivates its programmes.

No EBSU-specific faculty, department, programme or session records are preloaded. An administrator should enter the institution's approved structure. If 2025/2026 is still the current session, create it in Academic Management and use **Set current**.

## Production architecture
- **Application:** https://rollnexa.onrender.com/
- **GitHub:** https://github.com/Davidnna/RollNexa
- **Hosting:** Render (existing `rollnexa` web service)
- **Database:** Neon PostgreSQL (existing database)

The application uses `DATABASE_URL` (Neon pooled connection) and `DIRECT_DATABASE_URL` (Neon direct connection for migrations). Never commit these credentials.

## Upgrade from 0.2.1
1. Extract the `RollNexa_0.3.0_Academic_Structure.zip` package.
2. Upload the contents of its `rollnexa` folder to the root of the existing `Davidnna/RollNexa` repository, replacing existing files where prompted.
3. Ensure the new `academics/` and `templates/academics/` folders are uploaded.
4. Commit directly to `main` with: `Add academic structure management to RollNexa 0.3.0`.
5. Allow the existing Render service to deploy. Do not create a new Render service or Neon database.
6. The build runs Django checks, collects static files and applies the new migrations automatically.
7. Sign in as the existing system administrator and open `/management/academic/`.

## Database and migration safety
This release adds the `academics` app and three nullable academic-assignment fields to existing user profiles. The migration does not delete or recreate users, passwords, roles or existing records. Existing profiles remain valid and unassigned until an administrator edits their academic assignment.

Do not reset, recreate or manually alter the Neon database. If Render reports a migration error, stop and share the relevant deployment-log lines after removing secrets.

## Security
- Never commit `.env`, database URLs, passwords, API keys, bootstrap tokens or biometric information.
- Do not use real student or biometric data until privacy, security, retention, access and backup arrangements have been established.
- The temporary administrator bootstrap token should be removed from Render after the first administrator has been created.

For detailed upload and verification instructions, see `GITHUB_UPLOAD_GUIDE_0.3.0.md` and `RELEASE_NOTES_0.3.0.md`.
