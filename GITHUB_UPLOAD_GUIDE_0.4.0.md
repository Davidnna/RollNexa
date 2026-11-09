# GitHub and Render deployment — RollNexa 0.4.0

1. Extract `RollNexa_0.4.0_Course_Management_Release.zip`.
2. Open the extracted `rollnexa` folder.
3. Upload all its contents to the root of `Davidnna/RollNexa`, replacing existing files when prompted.
4. Ensure `academics/course_views.py`, `academics/course_forms.py`, `academics/course_urls.py`, `academics/migrations/0003_course_catalogue_and_offerings.py` and `templates/courses/` are present.
5. Commit to `main` with: `Add course catalogue and course offering management to RollNexa 0.4.0`.
6. Wait for Render to run Django checks, collect static files, apply migrations and deploy.
7. No new environment variables are required. Do not recreate or reset Neon.
8. Sign in as the system administrator and open `/management/courses/`.
9. Create course catalogue records, create offerings, assign lecturers, and open student registration when ready.

The migration adds four tables and supporting indexes/constraints. It does not delete or rewrite the existing EBSU academic structure or user accounts.
