# RollNexa 0.4.2 — Academic session and semester CSV import

## Deployment
1. Upload the release package contents into the existing GitHub repository root.
2. Commit to `main`.
3. Wait for Render to deploy the latest commit and run the existing database migrations.
4. No new environment variables or database are required.

## Import workflow
1. Sign in as a system administrator.
2. Open `/management/academic/sessions/import/`.
3. Download the EBSU starter CSV or blank template.
4. Upload the CSV and select Validate and preview.
5. Review all session and semester records.
6. Confirm the import.
7. Open Academic Management → Academic Sessions.
8. Select Set current on the academic session confirmed by the institution.
9. Open Academic Management → Semesters and set the current semester if required.
10. Return to Course Management and upload the course catalogue CSV.

## CSV columns
Required:
- `academic_session` — YYYY/YYYY.
- `session_start_date` — optional YYYY-MM-DD.
- `session_end_date` — optional YYYY-MM-DD.
- `semester` — FIRST, SECOND or SUMMER.
- `semester_start_date` — optional YYYY-MM-DD.
- `semester_end_date` — optional YYYY-MM-DD.

Optional:
- `source_url`
- `source_note`

Each row represents one semester under an academic session. Repeat the session name for each semester row.

## Safety
- New sessions and semesters are active but never automatically marked current.
- Existing current-session settings are preserved.
- Existing records are not deleted.
- Existing dates are not overwritten. If an existing date is blank, the importer may fill it from a supplied CSV value.
- Inactive matching records must be reactivated manually before import.
- The import is atomic and re-importing matching rows is idempotent.
- Semester dates must fall within the academic session dates when those dates are supplied.

## EBSU starter dataset limitations
The starter file includes 2025/2026 and 2026/2027 as candidate session records because EBSU has official admission-cycle references for those session names. It does not include dates and does not mark either session current. The EBSU academic calendar page currently surfaced by the public site is for 2023/2024, so the current undergraduate teaching session and the semester dates must be confirmed by the institution before setting a current session.
