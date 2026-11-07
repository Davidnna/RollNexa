# RollNexa 0.2.0 — User Management and Role-Based Access Control

## Included
- Adds a `UserProfile` model linked one-to-one to Django's existing user model.
- Adds `admin`, `lecturer` and `student` roles.
- Adds a data migration that creates profiles for all existing users without deleting or recreating them. Existing superusers become administrators; existing ordinary users become students.
- Removes public self-registration.
- Adds a protected one-time first-administrator setup route.
- Adds administrator-only student and lecturer account creation.
- Generates a temporary password for each created account and requires a password change at first sign-in.
- Adds account activation and deactivation.
- Adds role-specific dashboards and server-side access checks.
- Preserves the existing Neon database and the existing Django authentication records.

## Not included yet
- Academic faculties, departments, programmes and course registration.
- Lecturer-course assignment.
- QR-code attendance sessions.
- Facial enrollment or recognition.
- Attendance records, analytics and exports.
- Email delivery, email verification and password-reset email workflows.

## Required deployment action
Add `BOOTSTRAP_ADMIN_TOKEN` as a secret environment variable in Render before opening `/setup/initial-admin/`. Use a long, randomly generated value. After creating the first system administrator, remove this environment variable from Render. The route returns 404 when the token is absent or an administrator already exists.

## Existing accounts
The migration preserves all existing `auth_user` rows and creates a student profile for each ordinary account. The previously created test account remains available. It is not automatically promoted to administrator.
