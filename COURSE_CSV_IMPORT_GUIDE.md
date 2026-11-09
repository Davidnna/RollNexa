# RollNexa 0.4.1 — Course CSV Import Guide

## Deployment
1. Upload the release package contents into the existing GitHub repository root.
2. Commit to `main`.
3. Wait for Render to deploy and run migration `academics.0004_course_stress_code_and_units`.
4. No new environment variables or database are required.

## Prerequisites
- EBSU Faculty of Science exists and is active.
- Computer Science, Applied Biology, Industrial Chemistry, Industrial Mathematics and Applied Statistics, and Industrial Physics departments exist and are active.
- The Computer Science programme code `FSC-CS-P01` exists and is active.
- An active academic session is marked current.
- Active First and Second semester records exist under that current session.

If the session or semesters are missing, create them in Academic Management before importing. The EBSU CSV uses `CURRENT` rather than guessing an academic session name.

## Import
1. Sign in as a system administrator.
2. Open `/management/courses/import/`.
3. Download or upload `ebsu_computer_science_courses.csv`.
4. Select Validate and preview.
5. Resolve any validation errors.
6. Review new and unchanged course/offering counts.
7. Confirm the import.
8. Open the course catalogue and course offerings to verify the result.

## Data protection
- The importer does not delete records.
- Existing courses with conflicting details are not overwritten.
- Matching records are treated as unchanged.
- The import runs in one transaction.
- Imported offerings remain closed for registration.
- Re-uploading the same file is idempotent.
- Lecturer assignments and student registrations are not modified.

## Dataset limitations
The official EBSU page does not identify an academic session. The dataset uses the current session set in RollNexa. The course page may be reviewed by EBSU.
Service-course owning departments are mapped by course prefix to the matching Faculty of Science department; verify this mapping with the relevant departments.
GST courses are excluded because the imported 52-department academic structure does not include a General Studies department/unit.
CSC 442 is excluded because the official page does not publish its title.
Direct-entry curriculum sections marked "COMING SOON" are excluded.
`AR` is preserved as printed; the official page does not define it.
Source spellings "Algebra and Matrics" and "ContentArtificial Intelligence" are retained verbatim.
CSC 398 is imported with 18 units as published, which is why the release expands the allowed course-unit range to 30.
