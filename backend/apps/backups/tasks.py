# ===
# File Summary
# Path: backend\apps\backups\tasks.py
# Type: python
# Purpose: Backup service managing backup manifests, task scheduling, and restore metadata.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: create_scheduled_backup
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

from celery import shared_task

from apps.backups.services import create_backup


@shared_task
def create_scheduled_backup():
    manifest = create_backup()
    return {"backup_id": manifest.backup_id, "state": manifest.state}

