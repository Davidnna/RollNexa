# GitHub upload guide — RollNexa 0.5.0

## Before uploading

- Confirm the existing RollNexa deployment is healthy.
- Use the existing `Davidnna/RollNexa` repository and `main` branch.
- Do not create a new Render service or Neon database.
- Do not replace `.env` with real credentials or commit secrets.

## Upload

1. Download and extract `RollNexa_0.5.0_Lecturer_Management.zip`.
2. Open the extracted `rollnexa` folder.
3. Upload its contents into the root of the existing `Davidnna/RollNexa` repository, replacing matching files and preserving the repository's normal root layout.
4. Confirm that `academics/migrations/0007_lecturer_assignment_audit_history.py` is included.
5. Confirm that the updated `academics/models.py`, `academics/course_views.py`, `accounts/views.py`, URL files, templates, static CSS and release notes are included.
6. Commit directly to `main`.

## Commit message

`Add lecturer management, cross-department teaching assignments and assignment audit history in RollNexa 0.5.0`

## Deployment

Render should automatically deploy the existing web service. The existing build command runs checks, collects static files and applies the new migration. No new environment variables are required.

Do not manually run SQL against Neon and do not reset the database. If the deployment fails, stop and share the first relevant build or migration error lines after removing credentials and other secrets.

## Post-deployment verification

1. Confirm the Render deployment is **Live**.
2. Confirm the migration `academics.0007_lecturer_assignment_audit_history` completed.
3. Open `/management/lecturers/` as an administrator.
4. Open `/management/teaching-assignments/` as an administrator.
5. Assign a lecturer from a different department to a test offering; confirm that the cross-department label appears and the assignment is accepted.
6. Revoke the test assignment; confirm it appears under **Revoked history**.
7. Sign in as the lecturer and confirm the revoked offering no longer appears in **My teaching** and its roster URL returns not found.
8. Reassign the lecturer and confirm a new active assignment is created while the previous history record remains.

Use test accounts and test records until the institution approves real operational use.
