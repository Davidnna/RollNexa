# EBSU academic catalogue: sources and data-quality notes

Prepared for the RollNexa 0.3.1 starter import on 9 November 2026.

## Primary official sources

1. EBSU 2026/2027 approved cut-off marks: https://ebsu.edu.ng/ebsu-post-utme-approved-cut-off-mark-for-2026-2027-admission-exercise/
   - Used to identify the nine faculty groupings currently named in the 2026/2027 admission cut-off notice.
   - It names selected programmes explicitly (Medicine and Surgery, Anatomy, Physiology, Nursing Science, Medical Laboratory Science, Law, Accountancy, Mass Communication, Computer Science, Chemical Engineering, Civil Engineering, Electrical and Electronics Engineering, and Environmental Sciences).
2. EBSU 2026/2027 Post-UTME notice: https://ebsu.edu.ng/2026-2027-post-utme-application-screening/
   - The page itself is a 2026/2027 Post-UTME notice, but its embedded course catalogue is explicitly headed “Available Courses for 2025/2026 Academic Session”.
   - It is therefore used as the latest explicit published course list found during this research, not as proof that every listed programme is open in 2026/2027.
3. EBSU faculties directory: https://ebsu.edu.ng/faculties/
   - Used for faculty-directory labels and departmental/unit names.
   - The page appears to reflect an older structure: it lists Basic Medical Sciences and Clinical Medicine separately and does not show the Engineering and Environmental Science faculty grouping used in the 2026/2027 cut-off notice.
4. EBSU Department of Industrial Mathematics and Applied Statistics: https://ebsu.edu.ng/department-of-industrial-mathematics-and-applied-statistics/
   - States that the department offers B.Sc. Honours programmes in Mathematics, Industrial Mathematics and Statistics.
5. EBSU About page: https://ebsu.edu.ng/about-ebsu/
   - Historical background only; not treated as a current organisational chart.

## What the CSV contains

- 9 faculty records, using faculty groupings named in the 2026/2027 cut-off notice.
- 52 department/unit groupings assembled from the official faculties directory and the 2025/2026 admissions list.
- 81 programme/course names from the latest explicit undergraduate admissions list located, plus the three degree programme names stated on the Industrial Mathematics and Applied Statistics department profile.
- Internal RollNexa codes are generated for import consistency. They are not represented as official EBSU codes.
- The CSV uses the faculty wording “Faculty of Agriculture and Natural Resources Management” and “Faculty of Management Sciences” as published in the admissions/faculties directory; the 2026/2027 cut-off notice uses slightly different singular/plural wording for some of these faculty names.
- Programme awards and durations are left blank unless the official source states an award explicitly. The two B.A. labels for Theatre Arts and Film Production are taken from the 2025/2026 admissions list.
- The `mode` column is set to `full_time` for this regular UTME/Direct Entry catalogue. Work-and-Study/part-time offerings are not comprehensively catalogued here.

## Important caveats before operational use

The university's public pages are not fully synchronised. The current 2026/2027 cut-off notice identifies nine faculties, while the general faculties directory reflects an older grouping. The Post-UTME notice for 2026/2027 contains a course list labelled 2025/2026. Some directory items are not clearly identified as departments versus programmes/options. To make the CSV importable in RollNexa, certain option groups have been placed under a parent department as a provisional mapping. These rows contain notes and verification statuses explaining where the grouping requires confirmation.

In particular:

- The five Law subject areas listed on the faculties directory are grouped under a single “Law” department for this starter catalogue. Confirm this with the Faculty of Law/Registrar.
- Theatre Arts and Film Production are grouped under one unit for import purposes; confirm their approved departmental relationship.
- Environmental Sciences is used as a parent department for Architecture, Building, Environmental Management and Estate Management because the public admissions list does not provide a definitive departmental chart.
- Education options are grouped under the programme clusters shown in the admissions notice; confirm exact departmental reporting lines.
- The Faculty of Medicine grouping follows the 2026/2027 cut-off notice, while the older directory places Anatomy, Medicine and Surgery, and Physiology under Basic Medical Sciences.
- The older directory also lists Community Medicine, Internal Medicine, Pharmacology and Surgery under a separate Faculty of Clinical Medicine. These units are not included because the 2026/2027 cut-off notice's nine-faculty structure does not separately list Clinical Medicine and the undergraduate admissions list does not establish their current reporting line.
- No academic session dates or semester dates are preloaded. The university's current academic calendar must be checked separately before setting a current session/semester in RollNexa.

This is a research-based starter catalogue, not a Registrar-certified institutional master list. Before using it for real student enrolment, attendance assignment or official reporting, compare it with the current approved EBSU academic structure or obtain confirmation from the relevant Faculty Officers/Registrar. The CSV can be edited before import, and the import process previews all records before saving.
