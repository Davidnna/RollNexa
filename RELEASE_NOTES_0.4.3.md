# RollNexa 0.4.3 — Programme-specific course data and EBSU Science expansion

## Application changes
- Added programme-specific `credit_units` and `stress_code` to CourseOffering.
- Added per-offering `source_url` and `source_note` provenance fields.
- Migration 0005 backfills offering units/classification from existing course defaults.
- Migration 0006 adds offering provenance fields.
- Course CSV import stores units/classification/provenance per programme offering.
- Preview shows programme-specific units and classification.
- Existing non-empty course identities and offering provenance are protected from overwrite.
- Blank provenance on existing offerings can be populated by re-import.
- Student, lecturer and offering screens use programme-specific credit units.

## Data package
- `static/downloads/ebsu_science_curriculum_expanded.csv`: 785 course offerings across 11 Science programmes.
- `static/downloads/ebsu_course_curriculum_coverage.csv`: coverage register for all 81 programmes in the imported academic structure.
- `EBSU_SCIENCE_CURRICULUM_EXPANSION_NOTES.md`: source list, scope, exclusions and validation warnings.

## Limitations
- This is not yet the complete university-wide EBSU course catalogue. The other 70 programmes need approved departmental course outlines.
- GST courses are excluded until a General Studies service-unit owner can be represented in the academic data model.
- Elective-group selection rules are not yet enforced by RollNexa.
- Departmental verification is required before real student registration is opened.

## Deployment
- Commit to `main`; Render should deploy the application.
- Run migrations `academics.0005_offering_specific_units_and_stress` and `academics.0006_course_offering_provenance`.
- No new environment variables or database services are required.
