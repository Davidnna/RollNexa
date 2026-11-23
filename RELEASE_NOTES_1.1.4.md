# RollNexa 1.1.4 — CI reliability fixes

This maintenance release addresses the failures found in the 23 November 2026 GitHub Actions run.

## Changes

- Added `collectstatic --noinput` to the backend CI job before template tests. The production WhiteNoise manifest is now generated in CI, matching the Docker build.
- Updated the expired-QR endpoint test to authenticate through DRF's `APIClient`, isolating the expected expired-token response from SessionAuthentication's CSRF check.
- Added JSON parsing to the face-verification endpoint so JSON-only attempts to submit a client-side success boolean are rejected with HTTP 400. Successful face verification still requires the server-issued challenge and two uploaded camera frames.
- Corrected the invalid biometric-key test fixture to submit three frames, allowing it to reach the intended key-configuration check after request-shape validation.
- Explicitly close database connections inside each concurrency-test worker to prevent leftover PostgreSQL sessions from blocking test database teardown.
- Added deterministic ordering to lecturer attendance-session pagination.
- Upgraded GitHub Actions and Docker build actions to Node.js 24-compatible major versions.
- Updated application version metadata and deployment documentation to 1.1.4.

## Validation status

Static validation completed during packaging:

- Python source files compile successfully.
- GitHub Actions YAML files parse successfully.
- JavaScript configuration files pass `node --check`.
- Every static asset referenced by Django templates exists in `backend/static/`.

The previous hosted run `45115749357` passed migration checks and the React production build. It ran 192 Django tests but reported 52 errors caused by the uncollected WhiteNoise manifest, three test failures, and four remaining PostgreSQL sessions during test database teardown. The 1.1.4 changes target those findings.

**The corrected Django suite and Docker image have not yet been re-run in GitHub Actions.** The packaging environment does not contain Django or PostgreSQL, so this release must be verified by a new hosted CI run before it is treated as passing.
