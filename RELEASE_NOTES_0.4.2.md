# RollNexa 0.4.2 — Academic session and semester CSV import

## Added
- Administrator-only CSV import for academic sessions and semesters.
- Preview-before-import workflow.
- Session format and consecutive-year validation.
- First, Second and Summer semester validation.
- Optional session and semester date validation.
- Parent/child date-boundary validation.
- Atomic import and idempotent re-import.
- Existing dates are not overwritten; missing dates can be filled.
- Imported sessions and semesters are active but never automatically marked current.
- EBSU candidate session CSV for 2025/2026 and 2026/2027.
- Blank CSV template and source notes.
- Links from Academic Management and the session/semester lists.

## Database
No new database tables or schema migration are required. Existing `AcademicSession` and `Semester` models are used.

## Routes
- `/management/academic/sessions/import/`
- `/management/academic/sessions/import/template/`

## Deployment
No new environment variables are required. Existing Neon PostgreSQL settings remain unchanged.
