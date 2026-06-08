# Records And Admin QA Findings

Date: 2026-06-08

Status: passed after fixes.

## Coverage

- UI New Record flow creates a Product using the published object type and field labels.
- Records can be created, edited, released, archived, and protected from DELETE through API and UI checks.
- Record version snapshots can be created and listed.
- Record detail UI is checked for absence of Delete controls.
- Engineering users are blocked from configuration history and draft create/update/validate/publish endpoints.
- Configuration Admin can access admin workflows but cannot publish destructive field removals.
- React Admin navigation works, and direct `/admin` reload stays in the React app instead of falling through to Django admin.

## Findings Closed

- `QA-REC-001`: record archive flow was missing. Fixed with archived status, archive endpoint, audit event, and Playwright/API coverage.
- `QA-REC-002`: record versions were missing. Fixed with `RecordVersion`, migration, serializer, versions endpoint, and regression tests.
- `QA-ROUTE-001`: frontend `/admin` dev route fell through to Django admin. Fixed by removing the `/admin` proxy capture and adding a browser gate.
- Review-loop hardening added negative archive permission coverage and immutable version snapshot coverage.

## Evidence

- `frontend/e2e/client-readiness-records.spec.ts`
- `backend/tests/records/test_records.py`
- `frontend/vite.config.ts`
