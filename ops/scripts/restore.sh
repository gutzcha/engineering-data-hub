#!/bin/sh
set -eu

COMPOSE_FILE_ARGS=${COMPOSE_FILE_ARGS:-"-f compose.yaml"}
BACKUP_ID=${1:-}

if [ -z "$BACKUP_ID" ] || [ "${2:-}" ]; then
  echo "Usage: CONFIRM_RESTORE=<backup-id> $0 <backup-id>" >&2
  exit 2
fi

case "$BACKUP_ID" in
  [!A-Za-z0-9]*|*[!A-Za-z0-9_.:-]*)
    echo "Backup id must start with a letter or number and may contain only letters, numbers, dots, colons, dashes, and underscores." >&2
    exit 2
    ;;
esac

if [ "${CONFIRM_RESTORE:-}" != "$BACKUP_ID" ]; then
  echo "Refusing to restore without explicit confirmation." >&2
  echo "This will stop application services, replace the database, and replace managed/media files." >&2
  echo "Run: CONFIRM_RESTORE=$BACKUP_ID $0 $BACKUP_ID" >&2
  exit 2
fi

echo "Stopping application services before restore..."
docker compose $COMPOSE_FILE_ARGS stop proxy frontend beat worker backend

echo "Restoring PostgreSQL dump for backup $BACKUP_ID..."
docker compose $COMPOSE_FILE_ARGS exec -T -e RESTORE_BACKUP_ID="$BACKUP_ID" db sh -eu -c '
backup_dir="/data/backups/$RESTORE_BACKUP_ID"
dump_path="$backup_dir/database.dump"
test -f "$dump_path"
pg_restore --clean --if-exists --no-owner --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$dump_path"
'

echo "Restoring managed and media files..."
docker compose $COMPOSE_FILE_ARGS run --rm --no-deps -e RESTORE_BACKUP_ID="$BACKUP_ID" backend sh -eu -c '
backup_dir="/data/backups/$RESTORE_BACKUP_ID"
managed_root="${MANAGED_FILE_ROOT:-/data/managed}"
media_root="${MEDIA_ROOT:-/data/media}"

case "$managed_root" in /data/managed|/data/managed/*) ;; *) echo "Unsafe MANAGED_FILE_ROOT: $managed_root" >&2; exit 1 ;; esac
case "$media_root" in /data/media|/data/media/*) ;; *) echo "Unsafe MEDIA_ROOT: $media_root" >&2; exit 1 ;; esac

test -f "$backup_dir/managed-files.tar.gz"
test -f "$backup_dir/media-files.tar.gz"
mkdir -p "$managed_root" "$media_root"
find "$managed_root" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
find "$media_root" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar -xzf "$backup_dir/managed-files.tar.gz" -C "$managed_root"
tar -xzf "$backup_dir/media-files.tar.gz" -C "$media_root"
'

echo "Starting application services after restore..."
docker compose $COMPOSE_FILE_ARGS up -d backend worker beat frontend proxy
echo "Restore completed for $BACKUP_ID."
