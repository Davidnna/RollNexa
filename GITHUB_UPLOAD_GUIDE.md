# RollNexa 0.2.1 — GitHub and Render rebranding guide

## Phase 1 — Rename the existing Render service

1. Open https://dashboard.render.com/.
2. Open the existing AttendIQ web service.
3. Open **Settings** and locate the service name under its general settings.
4. Rename that existing service to `rollnexa`.
5. Confirm Render accepts the name and shows the intended `rollnexa.onrender.com` hostname. Availability is determined by Render; it is not guaranteed by this package.
6. Do not click **New Web Service** and do not create a new database.
7. If the name is unavailable or Render does not offer an in-place rename, stop and report what the dashboard displays. Do not improvise a second service.

The repository's `render.yaml` is updated to `name: rollnexa`. Renaming the existing service first ensures the Blueprint can match the intended resource by its new name. When reviewing a Blueprint sync, cancel if it proposes creating another web service.

## Phase 2 — Upload the rebranded source

1. Open the current repository: https://github.com/Davidnna/AttendIQ.
2. Download and extract `RollNexa_0.2.1_Rebrand.zip`.
3. Open the extracted `rollnexa` folder.
4. Select all its contents and upload them into the repository root using **Add file → Upload files**.
5. Replace existing files when GitHub prompts you.
6. Commit with this exact message:

   `Rebrand AttendIQ as RollNexa 0.2.1`

7. Open `REMOVALS.md` and delete the listed obsolete AttendIQ asset files and obsolete templates from GitHub. Commit those deletions with:

   `Remove obsolete AttendIQ branding assets`

## Phase 3 — Verify the deployment

1. Wait for the existing Render service to deploy successfully.
2. Open the new service URL shown by Render.
3. Check the landing page, favicon, logo, typography and colours.
4. Open `/healthz`; expected response: `ok`.
5. Sign in using the existing administrator or test account.
6. Confirm role-based dashboards and user management still work.
7. Check that the existing user record remains in Neon SQL Editor.

Do not change `DATABASE_URL`, `DIRECT_DATABASE_URL`, `SECRET_KEY`, `DEBUG` or the Neon database. This release has no database migration.

## Phase 4 — Rename the GitHub repository

After the Render deployment is verified:

1. Open the GitHub repository.
2. Select **Settings → General**.
3. Under **Repository name**, change `AttendIQ` to `RollNexa`.
4. Confirm **Rename**.
5. Use `https://github.com/Davidnna/RollNexa` for future links.

GitHub documents that repository web and Git operations at the old URL are redirected after a rename. Update future references to the new URL.

## Important safeguards
- Do not create a second Render web service.
- Do not delete the existing Render service.
- Do not create, reset, migrate or delete the Neon database.
- Do not share or commit secrets.
- If a Blueprint sync proposes creating a new service, cancel and ask for review before proceeding.
