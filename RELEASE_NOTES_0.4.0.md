# RollNexa 0.4.0 — Course Catalogue and Course Offering Management

## Purpose
This release builds the course-delivery layer on top of the academic structure introduced in 0.3.x. It separates reusable course catalogue records from programme-specific course offerings.

## Data model
- **Course:** master catalogue record owned by a department; contains course code, title, credit units and description.
- **CourseOffering:** a course offered to a particular degree programme and student level in a particular semester. The academic session is derived from the semester.
- **CourseLecturerAssignment:** associates an active lecturer account with a course offering.
- **CourseRegistration:** associates a student profile with an offering and records registered/withdrawn status.

The model permits a department's course to be offered to another department's programme. This supports service courses and avoids incorrectly requiring every course to be owned by the student's programme department.

## Administrator functionality
- Create, edit, search and deactivate courses.
- Create, edit and deactivate programme-specific course offerings.
- Set the offering's semester, level, registration status and optional enrolment capacity.
- Assign and remove lecturers.
- View registered student rosters.
- View course and enrolment summary counts.

## Student functionality
- View active offerings matching the student's assigned programme and current level.
- Register for an offering while registration is open.
- Withdraw while registration remains open.
- Duplicate registration is prevented.
- Optional offering capacity is enforced under a database row lock.

## Lecturer functionality
- View only active offerings assigned to the lecturer.
- View registered student rosters for assigned offerings.
- Lecturers cannot access course administration or other lecturers' offerings.

## Data integrity and access control
- Course code is unique within its owning department.
- A course offering is unique for course, programme, semester and level.
- A lecturer cannot be assigned twice to the same offering.
- A student cannot register twice for the same offering.
- Registration checks account role, account status, programme, level, offering status and registration-open status.
- Deactivation preserves historical offerings, assignments and registration records.
- Database records use PROTECT relationships to avoid accidental deletion of academic history.
- All write operations use POST forms with Django CSRF protection.

## Migration
Migration `academics.0003_course_catalogue_and_offerings` creates four new tables and indexes/constraints. It does not alter or delete existing faculties, departments, programmes, sessions, semesters, user profiles or Neon credentials.

## Not included
- QR-code generation, scanning or attendance marking.
- Facial enrollment or facial recognition.
- Attendance sessions, attendance records or analytics.
- Course add/drop approval workflow.
- Automatic email notifications.
- Timetable and examination scheduling.

These are separate subsequent milestones.
