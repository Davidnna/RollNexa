# GitHub upload guide — RollNexa 0.6.0

## Before uploading

- Confirm the existing RollNexa deployment is healthy.
- Use the existing `Davidnna/RollNexa` repository and `main` branch.
- Do not create a new Render service or Neon database.
- Do not commit `.env`, database URLs, passwords, tokens or biometric data.

## Upload

1. Extract `RollNexa_0.6.0_Attendance_Management.zip`.
2. Open the extracted `rollnexa` folder.
3. Upload its contents into the root of the existing `Davidnna/RollNexa` repository, replacing matching files and preserving the repository's normal root layout.
4. Confirm that the complete `attendance/` application is included, especially `attendance/migrations/0001_initial.py`.
5. Confirm that `config/settings.py`, `config/urls.py`, `templates/attendance/`, `templates/base.html`, `templates/accounts/lecturer_dashboard.html`, `static/css/app.css`, `README.md`, `VERSION` and the 0.6.0 release documents are included.
6. Commit to `main`.

## Commit message

`Add attendance session management foundation in RollNexa 0.6.0`

## Pre-deployment verification

Run these commands in a configured local environment:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The packaging environment did not have Django installed and had no package-index network access, so the runtime checks above have not been completed here. Do not deploy until they pass.

## Deployment

Render should deploy the existing web service. The existing build command applies the new `attendance.0001_initial` migration. No new environment variables are required.

Do not reset or recreate the Neon database. Do not run manual SQL. If Render reports a migration or application error, stop and share the first relevant log lines after removing secrets.

## Post-deployment verification

1. Confirm the Render deployment is Live and `attendance.0001_initial` completed.
2. Sign in as a lecturer with an active teaching assignment.
3. Open `/lecturer/attendance/` and schedule a session for an assigned active course offering.
4. Confirm a lecturer cannot select an offering to which they are not assigned.
5. Confirm overlapping non-cancelled sessions for the same offering are rejected.
6. Activate the session only within its configured time window, then close it.
7. Confirm students and unassigned lecturers cannot access lecturer session-management pages.
8. Confirm that no student is marked present merely because a session was activated.

QR scanning, facial enrolment/recognition and student check-in are not part of 0.6.0. Use test accounts and test records only.
