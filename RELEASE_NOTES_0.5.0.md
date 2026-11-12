# RollNexa 0.5.0 — Lecturer management and teaching assignment audit

## Purpose

This release completes the lecturer-management and teaching-assignment workflow on top of the lecturer accounts and basic offering assignments already introduced in 0.2.0 and 0.4.0. It does not replace the existing account, course catalogue, course offering, registration or Neon database architecture.

## Application changes

- Added an administrator-only lecturer directory at `/management/lecturers/` with search, department and account-status filters.
- Added lecturer profile details at `/management/lecturers/<profile_id>/`, including current teaching assignments and revoked assignment history.
- Added a central teaching-assignment register at `/management/teaching-assignments/` with create, search, active/history filters and revoke actions.
- Added assignment audit fields: assigning administrator, assignment date, active/revoked status, removal date, removing administrator and optional removal note.
- Replaced hard deletion of lecturer assignments with revocation. Historical assignment rows remain in the database.
- Changed uniqueness to permit one active assignment per lecturer/offering while allowing multiple historical assignment records.
- Added non-blocking cross-department assignment indicators. Lecturer home department remains unchanged when assigned to an offering owned by another department.
- Added cross-department labels to lecturer selection on an offering detail page and a clear warning on assignment-management pages.
- Lecturer dashboards now show active assignments and registered-student counts.
- Lecturer course and roster access now requires an active assignment.
- Deactivating a lecturer account automatically revokes that lecturer's active assignments and records the administrator and time. Reactivating the account does not silently restore old assignments; an administrator must explicitly assign the lecturer again.
- Updated course management copy to distinguish master-course identity from programme-specific offering units and classifications.

## Database migration

Migration: `academics.0007_lecturer_assignment_audit_history`

The migration:
- Adds assignment audit fields.
- Marks existing lecturer assignments as active, then revokes assignments belonging to lecturer accounts that were already inactive at upgrade time.
- Replaces the unconditional unique constraint with a conditional unique constraint applying only to active assignments.
- Adds indexes for lecturer/active and offering/active lookups.

Existing lecturer assignments are preserved. Their `assigned_by` value is blank because the previous release did not record who created them; the UI identifies these as legacy records. Assignments attached to lecturer accounts already inactive at upgrade time are moved into revoked history, with an explanatory note and no fabricated administrator identity. No course, offering, student, lecturer profile, academic session or enrolment record is deleted.

## Routes

- Lecturer directory: `/management/lecturers/`
- Lecturer profile: `/management/lecturers/<profile_id>/`
- Teaching assignments: `/management/teaching-assignments/`
- Lecturer's teaching: `/lecturer/courses/`
- Lecturer class roster: `/lecturer/courses/<offering_id>/`

## Security and permissions

- Only system administrators can manage lecturer profiles and teaching assignments.
- Lecturers can view only active offerings assigned to their own lecturer profile.
- Lecturer roster access is checked server-side against the active assignment; hiding a link is not used as an access-control mechanism.
- Students and other lecturers cannot open another lecturer's roster.
- Cross-department assignments are permitted by design and are not treated as an authorization exception.

## Deployment

- Commit the package to the existing `main` branch of `Davidnna/RollNexa`.
- Render should deploy the existing `rollnexa` web service.
- The existing `build.sh` runs `python manage.py check`, collects static files and applies migrations using `DIRECT_DATABASE_URL` when configured.
- No new environment variables, Render services or Neon databases are required.
- Do not reset or recreate the Neon database.

## Verification

The release includes regression tests for lecturer directory access, cross-department assignments, multiple lecturers per offering, assignment revocation and history, reassignment after revocation, lecturer-only roster access and automatic revocation when a lecturer account is deactivated.

Run `python manage.py test` after deployment or in a configured development environment. The package preparation environment did not have network access to install Django dependencies, so a full Django runtime test suite could not be executed during packaging; Python syntax, template block balance, route-name references, migration structure and package integrity were checked separately.
