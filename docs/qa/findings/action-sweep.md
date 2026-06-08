# Action Sweep Notes

Date: 2026-06-08

## Implemented Sweep Improvements

- Added `frontend/e2e/client-readiness-home.spec.ts` for live Home metrics and recent record links.
- Removed static detail IDs from `frontend/e2e/client-readiness-operations.spec.ts`.
- Added strict readiness gating with `frontend/e2e/support/strictReadiness.ts`.
- Added `frontend/e2e/client-readiness-population.spec.ts` for 20-PDF population.

## Final Sweep Requirements

The full browser sweep must be run with:

```powershell
$env:STRICT_CLIENT_READINESS='true'
$env:QA_POPULATE_FULL_DATASET='true'
npm --prefix frontend exec playwright test --project=chromium-desktop --forbid-only
npm --prefix frontend exec playwright test --project=chromium-mobile --forbid-only
```

Strict mode converts stack/user/population readiness failures into hard failures instead of skipped tests.

