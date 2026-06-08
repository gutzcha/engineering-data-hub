# Document Action Findings

Date: 2026-06-08

## Findings

Document action buttons did not behave like client-facing app UI:

- `Open` showed only repeated metadata.
- `Preview` opened raw JSON from `/api/documents/:id/preview/`.
- `Audit` opened raw JSON from `/api/documents/:id/audit/`.
- Existing documents had no user-visible Add Revision flow.

## Fixes

- `Preview` now routes to `/documents/:id?view=preview`.
- `Audit` now routes to `/documents/:id?view=audit`.
- Document detail renders formatted Preview and Audit panels.
- Document detail includes Add Revision.
- Download remains a direct file download.

## Regression Tests

- `frontend/src/features/documents/DocumentPanel.test.tsx`
- `frontend/src/app/clientReadinessStaticAudit.test.ts`

