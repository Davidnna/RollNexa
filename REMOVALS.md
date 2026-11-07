# Files to delete from the GitHub repository for AttendIQ 0.2.0

The 0.2.0 package removes public self-registration. After uploading the new files, delete these two obsolete templates in GitHub:

1. `templates/registration/signup.html`
2. `templates/core/dashboard.html`

They are no longer routed or used. Deleting them keeps the public repository aligned with the administrator-created account policy.

Do not delete the existing database or any Neon data.
