#!/bin/sh

# ===
# File Summary
# Path: ops\scripts\backup.sh
# Type: shell
# Purpose: Operational automation scripts and deployment helpers.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: file-level implementation
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 
set -eu

COMPOSE_FILE_ARGS=${COMPOSE_FILE_ARGS:-"-f compose.yaml"}
BACKUP_ID=${1:-}

if [ "${2:-}" ]; then
  echo "Usage: $0 [backup-id]" >&2
  exit 2
fi

case "$BACKUP_ID" in
  "")
    ;;
  [!A-Za-z0-9]*|*[!A-Za-z0-9_.:-]*)
    echo "Backup id must start with a letter or number and may contain only letters, numbers, dots, colons, dashes, and underscores." >&2
    exit 2
    ;;
esac

if [ -n "$BACKUP_ID" ]; then
  export BACKUP_ID
fi

docker compose $COMPOSE_FILE_ARGS exec -T -e BACKUP_ID="$BACKUP_ID" backend python manage.py shell -c '
import os
from apps.backups.services import create_backup

manifest = create_backup(backup_id=os.environ.get("BACKUP_ID") or None)
print(manifest.backup_id)
'

