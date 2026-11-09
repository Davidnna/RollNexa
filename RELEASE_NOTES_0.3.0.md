# RollNexa 0.3.0 — Academic Structure Management

## New capabilities
- Faculty management: create, edit, search, activate and deactivate faculties.
- Department management: associate each department with a faculty.
- Programme management: associate each programme with a department; capture programme code, award, duration and study mode.
- Academic session management: create sessions in YYYY/YYYY format, set one current session, and deactivate sessions without deleting history.
- Semester management: create first, second or summer semesters within an academic session; set one current semester, only within the current session.
- Academic administration dashboard with active record counts and current-period summary.
- Student profiles can be assigned to programmes and levels, including existing accounts through account editing.
- Lecturer profiles can be assigned to departments, including existing accounts through account editing.
- Existing user profiles remain valid; academic assignments are nullable until an administrator assigns them.
- Adds automated tests for academic access, hierarchy, session/semester current-state rules and account assignment.

## Data preservation
This release adds the `academics` app and new academic and account migrations. It does not delete or recreate existing users, passwords, account roles or database records. Existing students and lecturers remain unassigned until the administrator edits their academic assignment in User Management. Existing profiles have null department/programme and blank level by default.

## Deployment
The Render build automatically applies the new migrations. Continue using the existing Render service and Neon database. Do not create a new database and do not reset Neon.

## Initial data
No faculties, departments, programmes, sessions or semesters are preloaded. The administrator should enter the institution's approved academic structure. If 2025/2026 is the current session, create that session and use the **Set current** action; then create and set the current semester.

## Not included yet
- Course catalogue and course offerings.
- Lecturer-course allocation.
- Student course registration.
- QR-code generation, scanning and attendance sessions.
- Facial enrollment or recognition.
- Attendance records and reporting.
