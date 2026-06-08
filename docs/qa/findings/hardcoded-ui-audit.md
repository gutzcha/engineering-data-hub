# Hardcoded UI Audit

Date: 2026-06-08

## Findings

The audit found client-facing static/demo operational content in the React frontend:

- Home metrics were hardcoded instead of fetched from the API.
- Home recent activity used static records: `PE-1042`, `PE-1038`, `PE-1029`.
- Records page exposed an inert `Configure View` action.
- Dashboard header exposed implementation text: `Direct Load`.
- Task Inbox exposed a disabled `Find` button.
- Saved View status options did not match backend record states.

## Fixes

- Home metrics now come from `/records/`, `/workflow-tasks/?state=open`, and `/documents/`.
- Home recent records are live and clickable.
- Inert Records and Task Inbox controls were removed.
- Dashboard empty status is user-facing.
- Status choices are `draft`, `released`, and `archived`.

## Regression Guard

`frontend/src/app/clientReadinessStaticAudit.test.ts` fails if known fake Home values, inert `Configure View`, dashboard `Direct Load`, or raw document JSON links return.

