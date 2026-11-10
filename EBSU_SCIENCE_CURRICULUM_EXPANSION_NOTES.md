# EBSU Science curriculum expansion — RollNexa 0.4.3

## Dataset scope
This CSV contains 785 programme-specific course offerings across 11 Science programmes, including the original Computer Science starter curriculum. It is based on EBSU's published department curriculum pages and uses `CURRENT` for the academic session selected by the RollNexa administrator.

## Coverage
- Faculty of Science: Applied Biology, Applied Microbiology, Biochemistry, Biotechnology, Computer Science, Geology and Exploration Geophysics, Industrial Chemistry, Industrial Mathematics, Mathematics and Statistics, and Industrial Physics.
- The Industrial Mathematics and Applied Statistics department publishes separate programme curricula for Mathematics, Industrial Mathematics and Statistics.
- The CSV includes regular-entry curriculum offerings for 100–400 levels where the official page provides course code, title and credit units.
- The companion `ebsu_course_curriculum_coverage.csv` lists all 81 programmes in the imported academic structure and identifies programmes still requiring approved departmental course outlines.

## Source pages
- Applied Biology: https://ebsu.edu.ng/department-of-applied-biology/
- Applied Microbiology: https://ebsu.edu.ng/department-of-applied-microbiology/
- Biochemistry: https://ebsu.edu.ng/department-of-biochemistry/
- Biotechnology: https://ebsu.edu.ng/department-of-biotechnology/
- Computer Science: https://ebsu.edu.ng/department-of-computer-science/
- Geology: https://ebsu.edu.ng/department-of-geology/
- Industrial Chemistry: https://ebsu.edu.ng/department-of-industrial-chemistry/
- Industrial Mathematics and Applied Statistics: https://ebsu.edu.ng/department-of-industrial-mathematics-and-applied-statistics/
- Industrial Physics: https://ebsu.edu.ng/department-of-industrial-physics/

## Data modelling
- The same course code is stored once under its mapped owning department.
- Credit units and stress classification are stored per programme offering, because EBSU's published tables show that the same course code can have different units or classifications across programmes.
- Each offering stores its source URL and verification note.
- The importer creates offerings with registration closed.

## Exclusions and unresolved source issues
- GST courses are excluded because the imported 52-department structure does not include a General Studies department or service-unit owner. They should be added after a General Studies service-unit ownership model is agreed.
- Rows with missing course codes (including two Applied Microbiology 200-level Second Semester entries) are excluded.
- Ambiguous combined codes such as `ICH 261/263`, `ICH 331/332` and `PHY 253/261` are excluded pending departmental clarification.
- Unmapped prefixes such as `GSH`, `OHY`, `MCB`, `AGC5` and `M2A` are excluded because no matching owner unit is established in the imported academic structure.
- The Applied Microbiology page lists `BIO 102` twice in its 100-level Second Semester table, once for General Biology II and once for Practical Biology II. The duplicate-code practical row is excluded rather than silently changing its code.
- `BTE 403` is excluded because the official page leaves its credit value blank.
- The Industrial Physics page repeats its 400-level course list under both semesters. The repeated second-semester list is not duplicated in the CSV.
- Some published elective lists contain choice rules (e.g. select one, select three). RollNexa's current offering model records the listed elective courses but does not yet enforce elective-group selection rules.
- Several programme pages contain spelling differences or title variants for shared course codes. A single master course title is retained per department/code; the source note on each affected offering records the page's alternate wording.

## Important verification warning
These are public EBSU curriculum pages, not a Registrar-certified, dated course registration handbook for the 2025/2026 session. The dataset is a source-backed development and testing baseline. Before opening real student registration, obtain confirmation from the relevant Heads of Department/Faculty Officers and reconcile all differences against the current approved curriculum.

## Import
Upload `ebsu_science_curriculum_expanded.csv` at `/management/courses/import/` after RollNexa 0.4.3 is deployed and 2025/2026 is marked current. Preview first. The import should create one master course per owning department/code and one offering per programme/semester/level.
