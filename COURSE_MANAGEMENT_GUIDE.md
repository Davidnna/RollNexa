# RollNexa 0.4.0 — Course Management Guide

## Deployment
1. Extract the release ZIP.
2. Upload the contents of the `rollnexa` folder to the root of the existing RollNexa GitHub repository.
3. Replace existing files when prompted.
4. Commit to `main` with: `Add course catalogue and course offering management to RollNexa 0.4.0`
5. Wait for Render to finish the automatic deployment and migration.
6. No new environment variables are required. Do not create or reset the Neon database.

## Administrator setup order
1. Open `/management/courses/`.
2. Create the master course catalogue.
3. Create course offerings by selecting course, programme, semester and level.
4. Keep registration closed until the offering is ready.
5. Open the offering detail page and assign one or more lecturers.
6. Edit the offering and enable registration when ready.
7. Monitor the registered student roster.

## Course vs course offering
A course is a reusable catalogue record such as `CSC 301 — Data Structures`, owned by a department and assigned a credit-unit value.

A course offering represents delivery of that course to a particular programme and level in a particular semester/session. For example, CSC 301 may be offered to B.Sc. Computer Science, 300 level, First Semester, 2026/2027.

The same course may be offered to more than one programme, for example where it is a service course.

## Student setup
Before a student can register:
- The student account must be active.
- The administrator must assign the student's programme.
- The administrator must set the student's current level.
- A matching active course offering must exist.
- Registration must be open on that offering.

Students can register and withdraw through their own workspace. They cannot register for a different programme or level.

## Lecturer setup
Before a lecturer can see a course:
- The lecturer account must be active.
- The account role must be Lecturer.
- An administrator must assign the lecturer to the course offering.

Lecturers can view only their assigned active offerings and the students registered for those offerings.

## Verification checklist
- Administrator can create a course.
- Duplicate course code in the same department is rejected.
- Administrator can create a course offering.
- Duplicate offering for the same course/programme/semester/level is rejected.
- Lecturer can be assigned once to an offering.
- Student sees only matching programme/level offerings.
- Student can register when registration is open.
- Student cannot register when closed or for another programme/level.
- Duplicate registration is prevented.
- Capacity limit is enforced when configured.
- Lecturer can view their assigned class roster.
- Lecturer cannot access an offering not assigned to them.
- Existing EBSU academic structure and user accounts remain intact.

## Important
RollNexa 0.4.0 introduces course registration only. It does not yet record attendance. QR attendance will be implemented in a later release.
