# RollNexa

**Attendance, connected.**

RollNexa is a web-based Smart Academic Attendance Platform prototype. Its planned workflow connects academic users, attendance sessions, identity verification and institutional attendance records.

## Current release: 0.3.1 — EBSU catalogue and CSV import

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
- Administrator-only academic CSV import with validation, preview and atomic commit
- EBSU starter catalogue with source and verification notes
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

An EBSU starter catalogue is included under `static/downloads/ebsu_academic_structure.csv`. It is based on the university's published faculty directory and admissions information; some department groupings and programme details require institutional confirmation. Use the administrator-only CSV importer to preview and import it. The blank template is also downloadable from the importer. Academic session and semester dates are intentionally not preloaded; verify the current EBSU academic calendar before setting a current period.

## Production architecture
- **Application:** https://rollnexa.onrender.com/
- **GitHub:** https://github.com/Davidnna/RollNexa
- **Hosting:** Render (existing `rollnexa` web service)
- **Database:** Neon PostgreSQL (existing database)

The application uses `DATABASE_URL` (Neon pooled connection) and `DIRECT_DATABASE_URL` (Neon direct connection for migrations). Never commit these credentials.

## Upgrade from 0.3.0 or earlier
1. Extract the `RollNexa_0.3.1_EBSU_CSV_Import.zip` package.
2. Upload the contents of its `rollnexa` folder to the root of the existing `Davidnna/RollNexa` repository, replacing existing files where prompted.
3. Ensure `academics/csv_import.py`, the new `academics/migrations/0002_optional_programme_award_duration.py`, `templates/academics/import_csv.html` and `static/downloads/` are included.
4. Commit directly to `main` with: `Add EBSU academic catalogue and safe CSV import to RollNexa 0.3.1`.
5. Allow the existing Render service to deploy. Do not create a new Render service or Neon database.
6. The build runs Django checks, collects static files and applies migrations automatically.
7. Sign in as the existing system administrator and open `/management/academic/import/`.
8. Download the EBSU starter catalogue, validate it, review the preview and explicitly confirm the import.

## Database and migration safety
The 0.3.1 migration makes programme award and duration optional so unknown values are not invented. Existing values are retained. The academic CSV importer is additive/updating only, runs atomically, and does not delete or deactivate records. It does not change users, passwords, roles, student/lecturer assignments or academic sessions.

Do not reset, recreate or manually alter the Neon database. If Render reports a migration error, stop and share the relevant deployment-log lines after removing secrets.

## Security
- Never commit `.env`, database URLs, passwords, API keys, bootstrap tokens or biometric information.
- Do not use real student or biometric data until privacy, security, retention, access and backup arrangements have been established.
- The temporary administrator bootstrap token should be removed from Render after the first administrator has been created.

For detailed upload and verification instructions, see `GITHUB_UPLOAD_GUIDE_0.3.1.md`, `CSV_IMPORT_GUIDE.md`, `EBSU_DATA_SOURCES.md` and `RELEASE_NOTES_0.3.1.md`.


## Release 0.4.0 — Course catalogue and offerings

The course management module introduces:
- Department-owned master course records.
- Programme-, semester- and level-specific course offerings.
- Lecturer assignment to offerings.
- Student course registration and withdrawal.
- Lecturer class rosters.
- Role-specific access restrictions.

Administrator route: `/management/courses/`

Student route: `/student/courses/`

Lecturer route: `/lecturer/courses/`

See `COURSE_MANAGEMENT_GUIDE.md` and `RELEASE_NOTES_0.4.0.md` for deployment and verification instructions. Course registration is not attendance marking; QR attendance is a later release.


## Release 0.4.1 — Course CSV import

Administrators can bulk-import course catalogue records and programme-specific offerings at `/management/courses/import/`. The importer validates and previews the file before any database changes, uses an atomic transaction, preserves existing records and keeps registration closed.

Download the EBSU Computer Science starter CSV from the import page. See `EBSU_COMPUTER_SCIENCE_COURSE_DATA_NOTES.md` for source limitations, department mappings and setup prerequisites.
