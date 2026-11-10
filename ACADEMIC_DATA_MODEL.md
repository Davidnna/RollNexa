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

## Course catalogue and delivery (0.4.0)

- `Course`: reusable master course record owned by a department, with course code, title, credit units and description. A course code is unique within its owning department. Standard spaced codes such as `CSC 301` are accepted and normalised to uppercase. Credit units are constrained to 1–6.
- `CourseOffering`: delivery of a catalogue course to a specific programme and level in a specific semester. The academic session is derived from the semester. A course can be offered to programmes outside its owning department to support service courses. Each course/programme/semester/level combination is unique.
- `CourseLecturerAssignment`: associates an active lecturer profile with an offering. A lecturer can be assigned only once to a given offering.
- `CourseRegistration`: associates a student profile with an offering and records registered/withdrawn status. A student can have only one registration row per offering; re-registration updates the same row.

Students see offerings matching their assigned programme and current level. Registration is permitted only for active offerings with registration open, active academic parent records and an active student account. Optional offering capacity is enforced while locking the offering row in a database transaction. Lecturers see only offerings assigned to them and the roster for those offerings.

## CSV import

The system administrator can upload one UTF-8 CSV containing repeated faculty, department and programme values. RollNexa validates hierarchy, code formats, duplicate names/codes and existing database conflicts. It shows a preview before an explicit confirmation. The import is atomic and idempotent by scoped codes; it creates missing records and updates matching names/optional programme metadata. It never deletes or deactivates records. Blank award/duration cells do not erase existing values.

Internal codes in the EBSU starter catalogue are RollNexa identifiers, not official EBSU codes. Source URL, session, verification status and notes are retained in the CSV for traceability but are not stored as model fields.

## Integrity and retention

Academic foreign keys use `PROTECT` where deletion would break the hierarchy or historical references. The management interface uses deactivation, not deletion. Deactivating a faculty, department, programme, academic session or semester also deactivates dependent courses/offerings where relevant and closes registration. Existing lecturer assignments and course-registration records are retained. Reactivation is explicit and requires active parent records. Course-offering identity is locked after lecturer assignments or student registrations exist.

Course registrations are not attendance records. QR attendance, facial enrollment/verification and attendance history are separate future modules.


## Programme-specific course offering attributes
- A master `Course` stores the shared course identity (owning department, code, title and description) plus default unit/classification values for catalogue reference.
- A `CourseOffering` stores the programme-specific credit units and curriculum stress classification alongside programme, semester and level.
- The same master course may therefore be offered to multiple programmes with different unit values or classifications without creating duplicate course identities.
