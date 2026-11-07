# RollNexa 0.2.1 — Brand refresh

## Summary
Rebrands the existing AttendIQ 0.2.0 application as RollNexa without rebuilding the application or changing its database schema.

## Changes
- Product name: AttendIQ → RollNexa.
- Tagline: Attendance, connected.
- New RollNexa horizontal logo, standalone mark and favicon in SVG.
- Updated brand palette, logo placement, typography references and brand guidelines.
- Updated public landing page, login, dashboards, account-management screens, errors and Django administration labels.
- Updated page metadata and Render Blueprint service name.
- Updated repository and deployment instructions for the rename.

## Explicitly unchanged
- Django authentication model and existing user records.
- User profile schema, roles and permissions.
- Neon PostgreSQL database and connection strings.
- Render build/start commands, region and health check.
- QR attendance and facial verification remain planned, not implemented.

## Database migration
No database migration is included or required for this release.

## Deployment
Rename the existing Render service to `rollnexa` before syncing the updated Blueprint. If the Blueprint preview proposes creating a second service, cancel it. After the new branded deployment succeeds, rename the GitHub repository to `RollNexa`.
