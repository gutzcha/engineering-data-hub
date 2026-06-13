# Release Checklist

Use this checklist for pilot cutover, production updates, and release-candidate validation. Record command output, timestamps, and the person who performed each step in the change ticket.

## Preflight

- [ ] `.env` exists and production placeholders have been replaced.
- [ ] `APP_HOST`, `ALLOWED_HOSTS`, `DATABASE_URL`, `MEILI_MASTER_KEY`, `SECRET_KEY`, `BACKUP_ROOT`, and `MEDIA_ROOT` are set for the target environment.
- [ ] Internal DNS resolves `APP_HOST` to the release host.
- [ ] Pilot or production users know the maintenance window.

## Build And Start

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

For production, omit the development override:

```sh
docker compose -f compose.yaml up -d --build
```

- [ ] All required services build.
- [ ] `proxy`, `backend`, `frontend`, `worker`, `beat`, `db`, `redis`, and `meilisearch` are healthy or running.
- [ ] No long-running migration, worker, or proxy errors appear in logs.

## Migrations

Development:

```sh
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend python manage.py migrate
```

Production:

```sh
docker compose -f compose.yaml run --rm backend python manage.py migrate
```

- [ ] Migrations complete without unapplied migration warnings.
- [ ] The backend can connect to the configured database.

## Starter Configuration Publish

- [ ] Publish the starter Plastic Engineering configuration if this is a fresh environment.
- [ ] Confirm active configuration includes product, raw_material, product_spec, supplier, customer, project, test_method, and document object types.
- [ ] Confirm config-managed starter workflows and dashboards were bootstrapped after publish.

## Admin User Creation

- [ ] Create or verify a System Admin user.
- [ ] Confirm the user belongs to the `System Admin` group.
- [ ] Confirm the user can call `/api/accounts/me/` and access configuration, audit, backup, record, document, and workflow APIs.

## Storage And Certificates

- [ ] `BACKUP_ROOT` is writable by the backend and worker containers.
- [ ] A manual backup can write a manifest and database dump to the backup path.
- [ ] HTTPS certificate and key are mounted under `ops/caddy/certs/` or Caddy internal TLS is intentionally configured for development.
- [ ] Browser access to `https://<APP_HOST>` succeeds with the expected trust model.

## Health And Search

```sh
curl -k https://<APP_HOST>/api/health/
```

- [ ] Health endpoint returns `status: ok`.
- [ ] Database status is `ok`.
- [ ] Meilisearch is reachable from the backend.
- [ ] A known record or document can be indexed and found through `/api/search/?q=<term>`.

## Acceptance Tests

Focused backend traceability flow:

```sh
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps -e DJANGO_SETTINGS_MODULE=plastic_hub.settings.test backend pytest tests/e2e/test_traceability_flow.py
```

Frontend unit/lint checks:

```sh
docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm run lint
docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run
```

Playwright traceability flow against the Caddy/proxy origin. Run from the frontend package because Playwright is not installed at the repo root:

```sh
cd frontend
E2E_USERNAME=<test-user> E2E_PASSWORD=<test-password> npx playwright test e2e/traceability.spec.ts
```

Local development may create or update the provided test account only when explicitly opted in and the target host is local:

```sh
cd frontend
ALLOW_E2E_USER_SEEDING=true E2E_USERNAME=<test-user> E2E_PASSWORD=<test-password> npx playwright test e2e/traceability.spec.ts
```

- [ ] Backend e2e creates product, raw material, product spec, controlled PDF, workflow release, search results, and audit evidence.
- [ ] Frontend dependencies are installed and Playwright browser binaries are installed with `npx playwright install`.
- [ ] A pre-provisioned E2E account with System Admin or equivalent permissions is provided through `E2E_USERNAME` and `E2E_PASSWORD` for pilot or production targets.
- [ ] `ALLOW_E2E_USER_SEEDING=true` is used only with explicit test credentials against localhost, `127.0.0.1`, `::1`, or `plastic-hub.local`.
- [ ] Playwright uses `PLAYWRIGHT_BASE_URL` or defaults to `https://plastic-hub.local`.
- [ ] Playwright can reach Meilisearch through `PLAYWRIGHT_MEILI_URL` or defaults to `http://localhost:7700`.
- [ ] Traceability flow passes end to end.

## Release Decision

- [ ] Known defects are documented with owners.
- [ ] Backup and rollback path are approved.
- [ ] Release owner signs off.
- [ ] Pilot or production users are notified that the release is ready.


