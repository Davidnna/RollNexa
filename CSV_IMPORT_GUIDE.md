# RollNexa academic CSV import

Only a signed-in system administrator (Django superuser) can import academic data.

1. Open `/management/academic/`.
2. Select **Open CSV importer**.
   - The EBSU starter catalogue is also downloadable from this page.
   - Read `EBSU_DATA_SOURCES.md` before importing it; some department groupings are provisional because EBSU public pages do not present a single synchronised organisational chart.
3. Download the blank template or EBSU starter catalogue.
4. Upload a UTF-8 CSV and choose **Validate and preview file**.
5. Correct any reported errors. No records are saved during preview.
6. Review create/update/unchanged counts and the sample rows, then select **Confirm and import records**.

## Columns

Required: `faculty_code`, `faculty_name`.

Optional hierarchy: `department_code`, `department_name`, `programme_code`, `programme_name`. Department code and name must be supplied together. Programme code and name must be supplied together, and every programme must have a department.

Optional programme metadata: `award`, `duration_years`, `mode`. Leave award and duration blank if they have not been confirmed. `mode` accepts `full_time`, `part_time`, or blank (blank defaults to full-time for new records).

Optional provenance: `source_url`, `source_session`, `verification_status`, `notes`. These columns are kept in the CSV for traceability but are not written into the academic model.

Codes are internal RollNexa import identifiers, not necessarily official EBSU codes. Codes are used to match existing records on subsequent imports. Keep them stable.

The importer is additive/updating only. It never deletes or deactivates academic records. Existing users, passwords, roles and student/lecturer assignments are not changed. The import is atomic.
