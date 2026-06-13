# ===
# File Summary
# Path: backend\apps\folders\tasks.py
# Type: python
# Purpose: Folders domain handling templates, scans, change events, and review flows.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: scan_managed_folders
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

from apps.folders.scanner import scan_all_managed_folders


@shared_task
def scan_managed_folders():
    events = scan_all_managed_folders()
    return {"events": len(events)}

