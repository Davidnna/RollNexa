# RollNexa academic data model

## Institutional hierarchy

- `Faculty`: unique faculty code and name.
- `Department`: belongs to one faculty; department code and name are unique within that faculty.
- `Programme`: belongs to one department; programme code and name are unique within that department. Award and duration are optional because they must not be guessed when an official source does not state them. Study mode is full-time or part-time.

## Academic calendar

- `AcademicSession`: named `YYYY/YYYY`; optional start/end dates; at most one current session.
- `Semester`: belongs to one academic session; first, second or summer; optional start/end dates; at most one current semester. A current semester must belong to the current session.

## User assignment

- A student profile can reference a programme and current level. Its department is derived from the programme's department.
- A lecturer profile can reference a department.
- Existing profiles may remain unassigned until an administrator edits them.

## CSV import

The system administrator can upload one UTF-8 CSV containing repeated faculty, department and programme values. RollNexa validates hierarchy, code formats, duplicate names/codes and existing database conflicts. It shows a preview before an explicit confirmation. The import is atomic and idempotent by scoped codes; it creates missing records and updates matching names/optional programme metadata. It never deletes or deactivates records. Blank award/duration cells do not erase existing values.

Internal codes in the EBSU starter catalogue are RollNexa identifiers, not official EBSU codes. Source URL, session, verification status and notes are retained in the CSV for traceability but are not stored as model fields.

## Integrity and retention

Academic foreign keys use `PROTECT` where deletion would break the hierarchy or historical references. The management interface uses deactivation, not deletion. Deactivating a faculty deactivates its departments and programmes; deactivating a department deactivates its programmes; deactivating an academic session deactivates its semesters. Child records cannot be reactivated until their parent records are active.

Course catalogue, course offerings, lecturer-course allocation, student course registration and attendance records are outside this release.
