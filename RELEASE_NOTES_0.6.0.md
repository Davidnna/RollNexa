# RollNexa 0.6.0 — Attendance management foundation

## Purpose

This release establishes attendance-session management and the database/service foundation for the agreed dual-verification attendance workflow. It extends the existing Django, PostgreSQL, account, academic, course-offering and registration architecture. It does not replace the existing application or database.

## Application changes

- Added an `attendance` Django application.
- Added lecturer attendance-session scheduling for active course offerings to which the lecturer has an active teaching assignment.
- Added scheduled, active, closed and cancelled session states with explicit lifecycle timestamps and the lecturer account responsible for each transition.
- Added server-side checks for active academic records, lecturer assignment, valid time windows and overlapping non-cancelled sessions.
- Added lecturer session listing, detail, activation, closure and cancellation views.
- Added a class-roster view on each session, based on currently registered students.
- Added an `AttendanceRecord` model with one record per student per session and separate QR and facial verification timestamps.
- Added `record_verified_attendance`, a server-side service that rejects incomplete verification, inactive sessions, out-of-window verification, inactive students, unregistered students, offerings without an active lecturer assignment and duplicate records.
- Added a lecturer navigation link and dashboard entry for attendance sessions.

## Dual-verification rule

Attendance is recorded only when both verification services explicitly report success and both timestamps are supplied and valid:

1. QR Code verification must succeed.
2. Facial recognition must succeed after QR verification.
3. Both checks must occur within the active attendance-session time window.
4. The student must have an active account, a current registration and a programme/level profile that still matches the course offering.
5. A student can have only one attendance record per session.

The service stores verification timestamps, not raw face images or biometric templates.

## Current limitations

This release does not yet implement:

- QR Code generation, scanning or signed/expiring QR tokens.
- Facial enrolment, face capture, liveness detection or face matching.
- Student check-in pages or device-camera integration.
- Attendance analytics, absence calculation or report exports.

Activating a session does not mark any student present. The record service is an integration boundary for the subsequent QR and facial-verification releases.

## Database migration

Migration: `attendance.0001_initial`

The migration creates `AttendanceSession` and `AttendanceRecord`, including lifecycle and verification constraints, uniqueness constraints and query indexes. It depends on the existing `accounts.0003_rename_created_accounts_related_name` and `academics.0007_lecturer_assignment_audit_history` migrations.

The migration does not modify or delete existing users, academic structures, course offerings, lecturer assignments or course registrations. Do not reset or recreate the Neon database.

## Routes

- Lecturer session list: `/lecturer/attendance/`
- Schedule a session: `/lecturer/attendance/create/`
- Session detail: `/lecturer/attendance/<session_id>/`
- Activate a scheduled session: POST `/lecturer/attendance/<session_id>/activate/`
- Close an active session: POST `/lecturer/attendance/<session_id>/close/`
- Cancel a scheduled session: POST `/lecturer/attendance/<session_id>/cancel/`

## Security and permissions

- Only authenticated lecturer accounts can access lecturer attendance-session views.
- A lecturer can manage sessions only for an offering with an active teaching assignment.
- Students cannot access lecturer session-management routes.
- Session creation checks the offering's active academic hierarchy and rejects overlapping non-cancelled sessions.
- Attendance records require an active session, active student account, matching programme/level, current course registration, successful QR and facial verification outcomes, and both timestamps in the correct order.
- Database uniqueness prevents duplicate attendance for one student/session pair.
- No biometric image or template is collected or stored by this release.

## Deployment

- Upload the package contents to the existing `Davidnna/RollNexa` repository and `main` branch.
- Keep the existing Render web service and Neon database.
- Render's existing `build.sh` runs Django checks, collects static files and applies migrations.
- No new environment variables or hosting services are required.
- Do not manually alter the production database or reset migrations.

## Verification

The release includes tests for lecturer permissions, assignment-scoped offerings, session scheduling, overlap rejection, session lifecycle transitions, revoked-assignment access, dual-verification enforcement, duplicate prevention and student registration eligibility.

The packaging environment did not have Django installed and could not reach the package index. Python compilation checks passed, but the Django runtime test suite, migration autodetection and database migration have not been executed in this environment. Run `python manage.py check`, `python manage.py makemigrations --check --dry-run` and `python manage.py test` in a configured environment before deployment.
