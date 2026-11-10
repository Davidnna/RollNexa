# RollNexa 0.4.3 — Programme-specific course offering units

## Deployment
1. Upload the release package contents into the existing GitHub repository root.
2. Commit to `main`.
3. Wait for Render to deploy and run migration `academics.0005_offering_specific_units_and_stress`.
4. No new environment variables or database are required. Existing Neon PostgreSQL configuration remains unchanged.

## What changed
Credit units and curriculum classification now belong to a programme-specific course offering, not solely to the master course record. This reflects EBSU's published curricula, where the same course code can carry different credit units in different programmes (for example, BIO 101 is listed with 2 units in Computer Science and 3 units in Applied Biology).

The master course record still retains default credit-unit and stress-code values for catalogue reference. The authoritative values for enrolment, roster and attendance workflows are the fields on each offering.

## Import workflow
1. Sign in as a system administrator.
2. Open `/management/courses/import/`.
3. For the first expanded EBSU import, upload `ebsu_science_curriculum_expanded.csv` from `static/downloads/`. It contains 785 programme-specific offerings across 11 Science programmes. The companion `ebsu_course_curriculum_coverage.csv` lists all 81 programmes and the curriculum-source status for each.
4. Select Validate and preview.
5. Review new and unchanged course/offering counts and sample rows.
6. Confirm the import.
7. Verify programme-specific credit units on the Course Offerings page.

## CSV fields
- `faculty_code`, `department_code`, `course_code`, `course_title`: master course identity and owning department.
- `credit_units`, `stress_code`: values for this specific programme offering. They may differ for another programme using the same course code.
- `programme_code`, `academic_session`, `semester`, `level`: offering placement.
- `offering_active`, `registration_open`, `max_students`: offering controls. Imported offerings remain closed to registration.
- `description`: optional master-course description.
- `source_url`, `source_note`: optional provenance stored on each programme-specific offering and displayed on its detail page.

## Safety
- Existing course titles and descriptions are not overwritten.
- Existing offering credit units or classifications are not overwritten; a conflicting re-import is reported for review.
- Blank source URL/note fields on an existing offering may be filled from a new CSV; existing non-empty provenance is not overwritten.
- The import is atomic and idempotent.
- No lecturer assignments or student registrations are modified.
- Existing offering credit units and stress classifications are backfilled from the course master values during migration 0005.

## EBSU Science dataset scope
The supplied expanded dataset covers 11 Science programmes for which course-by-course curriculum tables were located in official EBSU department pages: Applied Biology, Applied Microbiology, Biochemistry, Biotechnology, Computer Science, Geology and Exploration Geophysics, Industrial Chemistry, Industrial Physics, Mathematics, Industrial Mathematics and Statistics. It contains 785 offering rows. It is not a complete 81-programme EBSU catalogue. The coverage register marks the other 70 programmes as requiring current approved departmental course outlines. GST and ambiguous/unmapped source rows are excluded; see `EBSU_SCIENCE_CURRICULUM_EXPANSION_NOTES.md`.
