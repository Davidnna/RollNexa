# RollNexa 0.3.1 — EBSU academic catalogue and CSV import

## Added
- Administrator-only CSV import for faculties, departments and programmes.
- Two-step workflow: validate/preview first, then explicitly confirm the import.
- UTF-8 CSV support, 1 MB and 2,000-row limits, strict column validation and row-level errors.
- Idempotent upsert by faculty, department and programme codes.
- Atomic import: a failed record rolls back the entire file.
- Import does not delete or deactivate records, and blank optional award/duration values do not overwrite existing values.
- Downloadable blank CSV template and EBSU starter catalogue (9 faculties, 52 department/unit groupings and 81 programme/course entries).
- Companion source notes document official EBSU URLs, the session labels on those sources and provisional department/programme mappings.
- Programme award and duration are now optional so unknown values are not fabricated.

## Database migration
- `academics.0002_optional_programme_award_duration` makes award and duration optional. Existing programme values are retained. The EBSU dataset leaves unknown awards and durations blank and flags provisional mappings in the CSV notes.

## Upgrade
Upload the complete `rollnexa/` folder to the existing `Davidnna/RollNexa` repository root and commit with:
`Add EBSU academic catalogue and safe CSV import to RollNexa 0.3.1`

Render applies the migration automatically. Do not reset or recreate Neon.
