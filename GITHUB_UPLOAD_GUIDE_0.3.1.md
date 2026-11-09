# RollNexa 0.3.1 GitHub upload guide

1. Extract the release ZIP.
2. Open the `rollnexa` folder.
3. Upload all its contents to the root of `Davidnna/RollNexa`, replacing existing files.
4. Ensure `academics/csv_import.py`, `academics/migrations/0002_optional_programme_award_duration.py`, `templates/academics/import_csv.html` and `static/downloads/` are included.
5. Commit to `main` with: `Add EBSU academic catalogue and safe CSV import to RollNexa 0.3.1`.
6. Wait for Render to run checks, collect static files, apply migrations and deploy.
7. Sign in as system administrator and open `/management/academic/import/`.
8. Download the EBSU starter catalogue, validate it, review the preview and confirm import.

Do not create a new Render service or Neon database. Do not reset the existing database.
