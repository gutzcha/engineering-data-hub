# Document QA Findings

Date: 2026-06-08

Status: passed after fixes.

## Coverage

- Downloads the real Plastic-Craft polycarbonate PDF from the internet and uploads it through the app as multipart form data.
- Verifies extracted preview text includes `polycarbonate` and material-property terms.
- Downloads PDF bytes back from the app and verifies PDF content type and file signature.
- Releases revision A, adds revision B, and verifies released revision A cannot be replaced.
- Verifies document `PATCH` and `DELETE` remain unavailable.
- Lists documents in the document workspace and retrieves document detail pages.
- Checks record-level document visibility through backend list/retrieve tests.

## Findings Closed

- `QA-DOC-001`: releasing a document revision failed on PostgreSQL due to a nullable joined `FOR UPDATE` query. Fixed by narrowing the lock query and adding a regression test.
- `QA-DOC-002`: the document workspace could not list or retrieve document metadata. Fixed with backend list/retrieve methods and React document library/detail rendering.

## Evidence

- `frontend/e2e/client-readiness-documents.spec.ts`
- `backend/apps/documents/views.py`
- `backend/tests/documents/test_revisions.py`
- `frontend/src/features/documents/DocumentPanel.tsx`
