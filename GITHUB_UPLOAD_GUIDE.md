# GitHub and Render upgrade guide — AttendIQ 0.2.0

## A. Update GitHub

1. Extract `AttendIQ_0.2.0_User_Management.zip`.
2. Open https://github.com/Davidnna/AttendIQ.
3. Choose **Add file → Upload files**.
4. Upload the extracted contents to the repository root, replacing files when GitHub indicates that a file already exists.
5. Ensure the new folders `accounts/migrations/` and `templates/accounts/` are present.
6. Commit directly to `main` with this exact message:

   `Add AttendIQ user management and role-based access control`

7. Delete the obsolete files listed in `REMOVALS.md`.

## B. Configure the first administrator

1. Open Render → AttendIQ → Environment.
2. Add `BOOTSTRAP_ADMIN_TOKEN`.
3. Generate a long random value using a password manager. Do not put the value in GitHub and do not share it in chat.
4. Save the environment variable and wait for the deployment to finish.
5. Open the public service URL followed by `/setup/initial-admin/`.
6. Enter the same token and create the first system administrator.
7. After successful setup, remove `BOOTSTRAP_ADMIN_TOKEN` from Render and save again.

## C. Verify

1. Sign in with the new administrator credentials.
2. Confirm the administrator dashboard opens.
3. Create one temporary student account.
4. Copy the temporary password from the one-time confirmation page and keep it securely.
5. Open a private/incognito browser window and sign in as the student.
6. Confirm AttendIQ requires a password change before allowing access to the student dashboard.
7. Confirm the existing test account remains in the database and now has the Student role.

## Important

- Do not create a new Neon database.
- Do not delete or reset existing database tables.
- Do not expose `DATABASE_URL`, `DIRECT_DATABASE_URL`, `SECRET_KEY` or `BOOTSTRAP_ADMIN_TOKEN`.
- If Render reports a migration error, stop and share the relevant log lines with secrets removed. Do not repeatedly redeploy or manually edit the Neon schema.
