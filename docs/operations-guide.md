# Operations Guide

## Hardware Recommendation

For a small engineering team, start with 4 CPU cores, 16 GB RAM, and 250 GB SSD storage. Use 8 CPU cores, 32 GB RAM, and separate SSD-backed storage for `/var/lib/docker` when document volume, OCR, or search indexing grows. Keep at least 2x the managed/media data size available for backup staging and restore drills.

## Docker Compose Install

Copy `.env.example` to `.env`, replace placeholders, then run:

```sh
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml exec backend python manage.py migrate
```

Development can use:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

The checked-in `.env.example` keeps Caddy on `tls internal` so a fresh Compose stack can start before production certificate files exist. Production should override this in `.env` with IT-provided certificate files.

## `.env` Setup

Set unique values for `SECRET_KEY`, `POSTGRES_PASSWORD`, `MEILI_MASTER_KEY`, `DATABASE_URL`, and `APP_HOST`. Set `TIME_ZONE` to the server/app time zone that should govern the 02:00 backup schedule. Do not reuse `.env.example` secrets in production. Backups store a fingerprint of known `.env` keys and values, but keys containing `PASSWORD`, `SECRET`, `TOKEN`, `KEY`, or `CREDENTIAL` are hashed instead of exported in clear text.

## Internal HTTPS Certificates

Ask IT for internal DNS pointing `APP_HOST` at the server and for certificate/key files trusted by company devices. Place the files under `ops/caddy/certs/` and set:

```env
CADDY_TLS_DIRECTIVE=tls /etc/caddy/certs/plastic-hub.crt /etc/caddy/certs/plastic-hub.key
```

The base Compose file mounts `ops/caddy/certs` read-only into the proxy container.

## VPN-Only Exposure

Only `proxy` publishes a host port, `443`. Keep PostgreSQL, Redis, Meilisearch, backend, and frontend ports on the Docker network in production. Restrict inbound `443` to the VPN or internal subnet with the host firewall or network security group.

## Backup Path Setup

`BACKUP_ROOT` defaults to `/data/backups`, backed by the `backup_files` Docker volume. The nightly Celery beat schedule runs at 02:00 server time and writes one directory per backup id. A manual backup can be run with:

```sh
sh ops/scripts/backup.sh
```

Use `COMPOSE_FILE_ARGS="-f compose.yaml -f compose.dev.yaml"` when running scripts against the development override.

## Restore Drill

Pick a backup id from `/api/backups/` or from `/data/backups`. Practice restore on a non-production copy first:

```sh
CONFIRM_RESTORE=<backup-id> sh ops/scripts/restore.sh <backup-id>
```

The restore script stops `proxy`, `frontend`, `beat`, `worker`, and `backend`, restores PostgreSQL from `database.dump`, replaces managed and media files, then starts application services again.

## Update Procedure

1. Run a fresh backup and record the backup id.
2. Pull or deploy the new application version.
3. Rebuild and start services with `docker compose -f compose.yaml up -d --build`.
4. Run `docker compose -f compose.yaml exec backend python manage.py migrate`.
5. Check health and scan worker/beat logs before releasing users.

## Health Checks

Use these checks after install, restore, and updates:

```sh
docker compose -f compose.yaml ps
docker compose -f compose.yaml logs --tail=100 backend worker beat proxy
curl -k https://<APP_HOST>/api/health/
```

The database, Redis, and Meilisearch services have Compose health checks. The backend health endpoint confirms the application can respond through Caddy.


