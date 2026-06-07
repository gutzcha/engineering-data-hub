#!/bin/sh
set -eu

COMPOSE_FILE_ARGS=${COMPOSE_FILE_ARGS:-"-f compose.yaml"}
BACKUP_ID=${1:-}

if [ "${2:-}" ]; then
  echo "Usage: $0 [backup-id]" >&2
  exit 2
fi

case "$BACKUP_ID" in
  *[!A-Za-z0-9_.:-]*)
    echo "Backup id may contain only letters, numbers, dots, colons, dashes, and underscores." >&2
    exit 2
    ;;
esac

if [ -n "$BACKUP_ID" ]; then
  export BACKUP_ID
fi

docker compose $COMPOSE_FILE_ARGS exec -T backend python manage.py shell -c '
import os
from apps.backups.services import create_backup

manifest = create_backup(backup_id=os.environ.get("BACKUP_ID") or None)
print(manifest.backup_id)
'
