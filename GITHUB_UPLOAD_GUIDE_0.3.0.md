# RollNexa 0.3.0 — GitHub upload and deployment guide

## 1. Upload the release
1. Download and extract `RollNexa_0.3.0_Academic_Structure.zip`.
2. Open the extracted `rollnexa` folder.
3. Upload its contents to the root of the existing `Davidnna/RollNexa` repository, replacing files where prompted.
4. Ensure the new `academics/` folder and `templates/academics/` folder are uploaded.
5. Commit directly to the `main` branch using:

   `Add academic structure management to RollNexa 0.3.0`

## 2. Render deployment
- Keep the existing Render service `rollnexa`.
- Keep the existing Neon database and existing environment variables.
- Do not create a new web service or database.
- Render should deploy automatically after the commit.
- The build runs `python manage.py check`, collects static files and applies migrations.

## 3. Verify after deployment
1. Open `/healthz` and confirm `ok`.
2. Sign in using the existing system administrator account.
3. Open `/management/academic/`.
4. Create a test faculty, department and programme.
5. Create an academic session such as `2025/2026` if it is the approved current session.
6. Set the session as current.
7. Create a semester under that session and set it as current.
8. Create a test student and assign a programme and level.
9. Create a test lecturer and assign a department.
10. Confirm the existing test user can still sign in.

## 4. Safety
- Do not manually delete or alter database tables.
- Do not run migrations manually in Neon SQL Editor.
- If Render reports a migration error, stop and share the relevant log lines after removing secrets.
- Academic records are deactivated rather than deleted.
