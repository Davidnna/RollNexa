# RollNexa 1.1.4 — Validation record

## Packaging checks completed

| Check | Result |
|---|---|
| Python source compilation (`compileall`) | Passed |
| GitHub Actions workflow YAML parsing | Passed |
| JavaScript configuration syntax (`node --check`) | Passed |
| Django template static references exist in `backend/static/` | Passed (16 references checked) |
| GitHub Actions runtime upgrades reviewed against current upstream documentation | Completed |

## Last hosted CI run available for diagnosis

GitHub Actions run: `45115749357` (23 November 2026)

| Job/check | Result |
|---|---|
| Django `check --deploy` | Completed with 2 HSTS warnings |
| `makemigrations --check --dry-run` | Passed |
| PostgreSQL migrations | Passed |
| `migrate --check` | Passed |
| React / TypeScript production build | Passed |
| Django tests | 192 executed; 52 errors and 3 failures |
| PostgreSQL test database teardown | Failed: 4 worker connections remained open |
| Docker image build | Not run because the backend job failed |

The 52 test errors all traced to the missing WhiteNoise static-files manifest entry for `images/favicon.svg`. The file itself is present in the source archive. The CI job did not run `collectstatic` before tests.

The three separate test failures were:
1. QR-expiry test returned 403 before reaching the endpoint assertion because the test used session authentication without a CSRF token.
2. JSON-only face-verification attempt returned 415 because the endpoint did not include `JSONParser`.
3. Invalid-key enrolment test submitted one frame, so request-shape validation returned 400 before the invalid-key check could be reached.

The two PostgreSQL concurrency tests themselves reported `ok`; their worker threads nevertheless left healthy persistent database connections open. `close_old_connections()` did not close those connections because they were not yet stale. The tests now call `connections.close_all()` within each worker.

## Warnings intentionally retained

`check --deploy` reports `security.W005` and `security.W021` because HSTS subdomain coverage and preload remain disabled in the Render Blueprint. They have not been enabled automatically: HSTS subdomain inclusion/preload should only be enabled after confirming every relevant subdomain is HTTPS-only and the deployment owner intends to make that commitment.

## Required release acceptance

A new GitHub Actions run must confirm:
- all Django tests pass;
- the test database is dropped cleanly;
- the frontend production build passes;
- the Docker image builds successfully.

Until that hosted run succeeds, the 1.1.4 source is a corrected candidate, not a CI-verified production release.
