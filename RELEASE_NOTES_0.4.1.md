# RollNexa 0.4.1 — Course CSV Import

## Added
- Administrator-only course and offering CSV upload.
- UTF-8 CSV parsing with a 2 MB file limit and 1,500-row limit.
- Required-column, code, credit-unit, stress-code, programme, academic-session, semester and level validation.
- Preview-before-import workflow.
- User-bound 15-minute import preview.
- Atomic import: a failure rolls back the entire import.
- Idempotent imports: matching existing records are unchanged.
- Existing course records with conflicting details are not overwritten.
- New offerings are imported with registration closed.
- CSV template and EBSU Computer Science starter dataset.
- Course stress-code field preserving EBSU's published C/R/E/G/AR values.
- Course unit range extended to 1–30 to preserve EBSU's published 18-unit SIWES entry.

## Data safety
- No course, offering, academic structure, student, lecturer or account is deleted.
- Existing course records are not overwritten.
- Import requires active faculty, department, programme, session and semester records.
- The academic session token `CURRENT` resolves to the active current session in RollNexa.
- All offering rows must identify a programme, semester and level.
- Registration cannot be opened by CSV import.

## Routes
- `/management/courses/import/`
- `/management/courses/import/template/`

## Migration
`academics.0004_course_stress_code_and_units` adds the stress-code field and expands the course credit-unit limit. It does not alter existing course records or delete existing data.

## Verification
Python syntax, Render YAML, template block balance, CSV header/row structure and ZIP integrity are checked during release packaging. Django runtime tests are included but must be executed in the deployment environment/CI.
