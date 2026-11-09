# EBSU Computer Science course dataset — source notes

## Primary source
Official Ebonyi State University, Department of Computer Science:
https://ebsu.edu.ng/department-of-computer-science/

The page lists course codes, titles, credit hours, stress codes, levels and semesters for the regular-entry Computer Science curriculum. The page states that its curriculum may be reviewed. It does not identify the academic session to which the table applies.

## Dataset contents
- 69 course-offering rows.
- 69 distinct course catalogue records.
- One programme code: `FSC-CS-P01` (a RollNexa internal identifier generated in the imported academic-structure starter catalogue; it is not represented as an official EBSU programme code).
- Levels 100, 200, 300 and 400.
- First and second semesters.
- `academic_session=CURRENT` resolves to the academic session marked current in RollNexa.
- All imported offerings are active but registration remains closed.

## Department mapping
The EBSU curriculum page states that faculty-common courses are described in the curriculum of the department offering them, and gives MAT 101 as an example. To make service courses usable in RollNexa, the dataset maps subject prefixes to the corresponding departments in the imported Faculty of Science structure:
- CSC → FSC-CS (Computer Science)
- BIO → FSC-AB (Applied Biology)
- ICH → FSC-ICH (Industrial Chemistry)
- MAT and STA → FSC-IMAS (Industrial Mathematics and Applied Statistics)
- PHY → FSC-IP (Industrial Physics)

This mapping is an informed administrative mapping based on subject prefixes and EBSU's published department list; it must be confirmed by the relevant EBSU departments before production use.

## Exclusions and unresolved source issues
- GST 101, GST 102, GST 103, GST 106, GST 107, GST 201, GST 202, GST 301 and GST 302 are not included because the imported 52-department catalogue has no General Studies department code to own them. Do not assign them to Computer Science merely to force an import. Add the correct General Studies unit/department once EBSU confirms its administrative owner.
- CSC 442 is excluded because the official page shows its credit hours and stress code but no course title.
- Generic elective placeholder rows are excluded; named elective options are included individually. RollNexa 0.4.1 does not yet enforce the curriculum's 'choose one', 'choose any two' or alternative-course selection rules.
- Direct-entry curriculum sections marked "COMING SOON" are excluded.
- The source uses `AR` in some rows without defining it in its course-code explanation. The CSV preserves `AR` literally and does not expand its meaning.
- The source spells MAT 101 as "Algebra and Matrics" and displays CSC 422 as "ContentArtificial Intelligence". These titles are preserved verbatim rather than silently corrected.
- SIWES (CSC 398) is listed as 18 credit hours. RollNexa 0.4.1 extends the course-unit validation range to 1–30 to preserve this published value.

## Import prerequisites
Before uploading:
1. Ensure Faculty of Science, the departments listed above, and the Computer Science programme exist and are active.
2. Create an active academic session and mark it current.
3. Create active First and Second semester records under that current session.
4. Upload the CSV through the administrator-only Course CSV Import page.
5. Review the preview. All new offerings are imported with registration closed.
6. Open registration manually only after confirming the course and lecturer setup.

## CSV semantics
- `CURRENT` means use the active current academic session in RollNexa.
- `FIRST`, `SECOND`, and `SUMMER` identify the semester.
- `registration_open` must be `false` on import; registration is opened manually from the offering workflow.
- Existing course records are not overwritten. If a code already exists with different details, the preview reports a conflict for manual reconciliation.
- Re-uploading the same CSV is idempotent: matching courses and offerings are reported as unchanged.


## Important academic validation
The source page is the university's published department curriculum page, not a dated course registration handbook for a named academic session. It states that the curriculum may be reviewed. The dataset is therefore suitable as a structured test starter and requires confirmation against the current approved departmental course outline before official student registration.
