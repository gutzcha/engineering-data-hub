from celery import shared_task

from apps.folders.scanner import scan_all_managed_folders


@shared_task
def scan_managed_folders():
    events = scan_all_managed_folders()
    return {"events": len(events)}
